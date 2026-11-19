from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.matches.models import Match
from apps.playoffs.forms import PlayoffSettingsForm
from apps.playoffs.models import LeagueSettings, Playoff, PlayoffMatch, PlayoffTie
from apps.playoffs.services import (
    generate_playoff,
    calculate_tie_winner,
    confirm_tie_result_change,
    get_league_settings,
    get_teams_classified,
    get_tie_aggregate,
    has_played_downstream_match,
    has_conflicting_downstream_slot,
    get_next_schedulable_round,
    record_penalty_result,
    resolve_tie,
    sync_playoff_advancement,
)
from apps.teams.models import Team
from apps.tournaments.models import MatchDay, Tournament
from apps.users.models import User


class PlayoffGenerationTests(TestCase):
    def setUp(self):
        self.teams = [
            Team.objects.create(name=f"Team {index}", coach="Coach", category="seniors")
            for index in range(1, 9)
        ]
        self.settings = LeagueSettings.objects.create(category="seniors", playoffs_enabled=True)

    def test_generates_seeded_quarterfinals_and_pending_rounds(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))

        quarterfinals = playoff.ties.filter(round=PlayoffTie.QUARTERFINAL).order_by("position")
        self.assertEqual(quarterfinals.count(), 4)
        self.assertEqual(quarterfinals.first().home_team, self.teams[0])
        self.assertEqual(quarterfinals.first().away_team, self.teams[-1])
        self.assertEqual(playoff.ties.filter(round=PlayoffTie.SEMIFINAL).count(), 2)
        semifinal_one = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        semifinal_two = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=2)
        quarterfinals_by_position = {tie.position: tie for tie in quarterfinals}
        self.assertEqual(quarterfinals_by_position[1].next_tie, semifinal_one)
        self.assertEqual(quarterfinals_by_position[4].next_tie, semifinal_one)
        self.assertEqual(quarterfinals_by_position[2].next_tie, semifinal_two)
        self.assertEqual(quarterfinals_by_position[3].next_tie, semifinal_two)
        self.assertEqual(quarterfinals_by_position[1].next_slot, "home")
        self.assertEqual(quarterfinals_by_position[4].next_slot, "away")
        self.assertEqual(quarterfinals_by_position[2].next_slot, "home")
        self.assertEqual(quarterfinals_by_position[3].next_slot, "away")
        self.assertTrue(playoff.ties.filter(round=PlayoffTie.FINAL).exists())
        self.assertTrue(playoff.ties.filter(round=PlayoffTie.THIRD_PLACE).exists())

    def test_home_and_away_creates_two_legs_with_best_seed_at_home_second(self):
        self.settings.playoffs_home_and_away = True
        self.settings.save(update_fields=["playoffs_home_and_away"])

        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))

        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        self.assertEqual(tie.first_leg.home_team, self.teams[-1])
        self.assertEqual(tie.second_leg.home_team, self.teams[0])

        self.assertEqual(tie.first_leg.match_day.description, "Cuartos de final (ida)")
        self.assertEqual(tie.second_leg.match_day.description, "Cuartos de final (vuelta)")
        self.assertEqual(MatchDay.objects.filter(category="seniors").count(), 2)

    def test_tied_single_match_requires_penalties_and_advances_winner(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        tie.first_leg.home_score = 1
        tie.first_leg.away_score = 1
        tie.first_leg.status = "finished"
        tie.first_leg.save()

        with self.assertRaises(ValidationError):
            resolve_tie(tie)

        resolved_tie = record_penalty_result(tie, 5, 4)
        semifinal = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        self.assertEqual(resolved_tie.winner, tie.home_team)
        self.assertEqual(semifinal.home_team, tie.home_team)

    def test_changed_result_requires_confirmation_before_reseeding_unplayed_rounds(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        match = tie.first_leg
        match.home_score, match.away_score = 2, 0
        match.status = "finished"
        match.save()
        resolve_tie(tie)
        old_winner = tie.home_team

        match.home_score, match.away_score = 0, 3
        match.save(update_fields=["home_score", "away_score"])

        self.assertEqual(calculate_tie_winner(tie), tie.away_team)
        with self.assertRaises(ValidationError):
            resolve_tie(tie)
        tie.refresh_from_db()
        self.assertEqual(tie.winner, old_winner)

        updated_tie = confirm_tie_result_change(tie)
        semifinal = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        semifinal.refresh_from_db()
        self.assertEqual(updated_tie.winner, tie.away_team)
        self.assertEqual(semifinal.home_team, tie.away_team)

    def test_conflicting_existing_slot_requires_confirmation_even_if_winner_is_unchanged(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        match = tie.first_leg
        match.home_score, match.away_score = 2, 0
        match.status = "finished"
        match.save()
        resolve_tie(tie)
        tie.refresh_from_db()
        semifinal = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        semifinal.home_team = self.teams[2]
        semifinal.save(update_fields=["home_team"])

        self.assertEqual(calculate_tie_winner(tie), tie.winner)
        self.assertTrue(has_conflicting_downstream_slot(tie, tie.winner))
        with self.assertRaises(ValidationError):
            resolve_tie(tie)

        confirm_tie_result_change(tie)
        semifinal.refresh_from_db()
        self.assertEqual(semifinal.home_team, tie.winner)

    def test_changed_result_cannot_reseed_a_played_downstream_round(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        match = tie.first_leg
        match.home_score, match.away_score = 1, 0
        match.status = "finished"
        match.save()
        resolve_tie(tie)

        semifinal = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        downstream_match = Match.objects.create(
            home_team=tie.home_team,
            away_team=tie.away_team,
            date=date(2026, 6, 15),
            time=time(15, 0),
            status="finished",
        )
        PlayoffMatch.objects.create(tie=semifinal, match=downstream_match, leg=PlayoffMatch.SINGLE)
        match.home_score, match.away_score = 0, 2
        match.save(update_fields=["home_score", "away_score"])

        self.assertTrue(has_played_downstream_match(tie))
        with self.assertRaises(ValidationError):
            confirm_tie_result_change(tie)
        tie.refresh_from_db()
        self.assertEqual(tie.winner, tie.home_team)

    def test_tied_correction_waits_for_penalties_before_reseeding_scheduled_round(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        match = tie.first_leg
        match.home_score, match.away_score = 1, 0
        match.status = "finished"
        match.save()
        resolve_tie(tie)
        semifinal = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        future_match = Match.objects.create(
            home_team=tie.home_team,
            away_team=tie.away_team,
            date=date(2026, 6, 20),
            time=time(15, 0),
            status="scheduled",
        )
        PlayoffMatch.objects.create(tie=semifinal, match=future_match, leg=PlayoffMatch.SINGLE)
        match.home_score, match.away_score = 1, 1
        match.save(update_fields=["home_score", "away_score"])

        with self.assertRaises(ValidationError):
            confirm_tie_result_change(tie)

        tie.refresh_from_db()
        self.assertEqual(tie.winner, tie.home_team)
        future_match.refresh_from_db()
        self.assertEqual(future_match.status, "scheduled")

    def test_playoffs_view_flags_conflicting_scheduled_slot_without_rewriting_it(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        match = tie.first_leg
        match.home_score, match.away_score = 1, 0
        match.status = "finished"
        match.save()
        semifinal = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        semifinal.home_team = tie.away_team
        semifinal.save(update_fields=["home_team"])
        future_match = Match.objects.create(
            home_team=tie.away_team,
            away_team=tie.home_team,
            date=date(2026, 6, 20),
            time=time(15, 0),
            status="scheduled",
        )
        PlayoffMatch.objects.create(tie=semifinal, match=future_match, leg=PlayoffMatch.SINGLE)
        organizer = User.objects.create_user(username="sync-organizer", password="secret", role="ORGANIZER")
        self.client.force_login(organizer)

        response = self.client.get(reverse("playoffs"), {"category": "seniors"})

        self.assertContains(response, "cambia el clasificado")
        self.assertContains(response, "Confirmar actualización del cuadro")
        tie.refresh_from_db()
        semifinal.refresh_from_db()
        future_match.refresh_from_db()
        self.assertIsNone(tie.winner)
        self.assertEqual(semifinal.home_team, tie.away_team)
        self.assertEqual((future_match.home_team, future_match.away_team), (tie.away_team, tie.home_team))

    def test_view_sync_does_not_reseed_after_saved_winner_becomes_stale(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        match = tie.first_leg
        match.home_score, match.away_score = 2, 0
        match.status = "finished"
        match.save()
        resolve_tie(tie)

        semifinal = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        semifinal.home_team = self.teams[2]
        semifinal.away_team = self.teams[3]
        semifinal.save(update_fields=["home_team", "away_team"])
        future_match = Match.objects.create(
            home_team=self.teams[2],
            away_team=self.teams[3],
            date=date(2026, 6, 20),
            time=time(15, 0),
            status="scheduled",
        )
        PlayoffMatch.objects.create(tie=semifinal, match=future_match, leg=PlayoffMatch.SINGLE)
        match.home_score, match.away_score = 0, 3
        match.save(update_fields=["home_score", "away_score"])

        response = self.client.get(reverse("playoffs"), {"category": "seniors"})

        self.assertContains(response, "cambia el clasificado")
        semifinal.refresh_from_db()
        future_match.refresh_from_db()
        self.assertEqual((semifinal.home_team, semifinal.away_team), (self.teams[2], self.teams[3]))
        self.assertEqual((future_match.home_team, future_match.away_team), (self.teams[2], self.teams[3]))

    def test_organizer_can_record_penalties_from_playoff_bracket_and_advance_winner(self):
        self.settings.playoffs_home_and_away = True
        self.settings.save(update_fields=["playoffs_home_and_away"])
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        first_leg = tie.first_leg
        second_leg = tie.second_leg
        first_leg.home_score, first_leg.away_score = 0, 1
        first_leg.status = "finished"
        first_leg.save()
        second_leg.home_score, second_leg.away_score = 0, 1
        second_leg.status = "finished"
        second_leg.save()

        organizer = User.objects.create_user(username="organizer", password="secret", role="ORGANIZER")
        self.client.force_login(organizer)

        bracket_response = self.client.get(reverse("playoffs"), {"category": "seniors"})
        self.assertContains(bracket_response, "Empate global: 1 - 1")
        self.assertContains(bracket_response, "Registra los penales")

        response = self.client.post(
            reverse("record_playoff_penalties", args=[tie.pk]),
            {"home_penalties": "5", "away_penalties": "4"},
            query_params={"category": "seniors"},
        )

        self.assertRedirects(response, f"{reverse('playoffs')}?category=seniors")
        tie.refresh_from_db()
        self.assertEqual(tie.winner, tie.home_team)
        semifinal = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        semifinal.refresh_from_db()
        self.assertEqual(semifinal.home_team, tie.home_team)
        self.assertEqual((tie.home_penalties, tie.away_penalties), (5, 4))

    def test_non_organizer_cannot_record_playoff_penalties(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        user = User.objects.create_user(username="player", password="secret", role="PLAYER")
        self.client.force_login(user)

        response = self.client.post(
            reverse("record_playoff_penalties", args=[tie.pk]),
            {"home_penalties": "5", "away_penalties": "4"},
            query_params={"category": "seniors"},
        )

        self.assertEqual(response.status_code, 403)

    def test_aggregate_winner_advances_when_match_points_are_tied(self):
        self.settings.playoffs_home_and_away = True
        self.settings.save(update_fields=["playoffs_home_and_away"])
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        first_leg = tie.first_leg
        second_leg = tie.second_leg

        # The away team wins the first leg 5-0; the home team wins the return 1-0.
        first_leg.home_score, first_leg.away_score = 5, 0
        first_leg.status = "finished"
        first_leg.save()
        second_leg.home_score, second_leg.away_score = 1, 0
        second_leg.status = "finished"
        second_leg.save()

        self.assertEqual(get_tie_aggregate(tie), (1, 5))
        resolved_tie = resolve_tie(tie)
        self.assertEqual(resolved_tie.winner, tie.away_team)

    def test_aggregate_tie_requires_penalties(self):
        self.settings.playoffs_home_and_away = True
        self.settings.save(update_fields=["playoffs_home_and_away"])
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        first_leg, second_leg = tie.first_leg, tie.second_leg

        first_leg.home_score, first_leg.away_score = 1, 0
        first_leg.status = "finished"
        first_leg.save()
        second_leg.home_score, second_leg.away_score = 1, 0
        second_leg.status = "finished"
        second_leg.save()

        self.assertEqual(get_tie_aggregate(tie), (1, 1))
        with self.assertRaises(ValidationError):
            resolve_tie(tie)

        resolved_tie = record_penalty_result(tie, 5, 4)
        self.assertEqual(resolved_tie.winner, tie.home_team)

    def test_generation_is_blocked_while_regular_matches_are_pending(self):
        Match.objects.create(
            home_team=self.teams[0],
            away_team=self.teams[1],
            date=date(2026, 5, 30),
            time=time(10, 0),
            status="scheduled",
        )

        with self.assertRaises(ValidationError):
            generate_playoff("seniors", date(2026, 6, 1), time(10, 0))

        self.assertFalse(PlayoffTie.objects.filter(playoff__category="seniors").exists())

    def test_non_power_of_two_bracket_uses_top_seed_byes(self):
        self.settings.teams_classified = 6
        self.settings.save(update_fields=["teams_classified"])

        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))

        quarterfinals = list(playoff.ties.filter(round=PlayoffTie.QUARTERFINAL).order_by("position"))
        self.assertEqual(len(quarterfinals), 4)
        self.assertTrue(quarterfinals[0].is_bye)
        self.assertTrue(quarterfinals[1].is_bye)
        self.assertEqual(quarterfinals[0].winner, self.teams[0])
        self.assertEqual(quarterfinals[1].winner, self.teams[1])
        self.assertEqual((quarterfinals[2].home_team, quarterfinals[2].away_team), (self.teams[2], self.teams[5]))
        self.assertEqual((quarterfinals[3].home_team, quarterfinals[3].away_team), (self.teams[3], self.teams[4]))
        self.assertEqual(PlayoffMatch.objects.filter(tie__playoff=playoff).count(), 2)
        self.assertIsNone(get_next_schedulable_round(playoff))

        for tie in quarterfinals[2:]:
            match = tie.first_leg
            match.home_score, match.away_score = 1, 0
            match.status = "finished"
            match.save()
            resolve_tie(tie)

        semifinal_one = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        semifinal_two = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=2)
        self.assertEqual((semifinal_one.home_team, semifinal_one.away_team), (self.teams[0], self.teams[3]))
        self.assertEqual((semifinal_two.home_team, semifinal_two.away_team), (self.teams[1], self.teams[2]))
        self.assertEqual(get_next_schedulable_round(playoff), PlayoffTie.SEMIFINAL)

    def test_playoff_view_displays_bye_advancement(self):
        self.settings.teams_classified = 6
        self.settings.save(update_fields=["teams_classified"])
        generate_playoff("seniors", date(2026, 6, 1), time(10, 0))

        response = self.client.get(reverse("playoffs"), {"category": "seniors"})

        self.assertContains(response, "avanza directamente")
        self.assertNotContains(response, "Pasa al siguiente partido")

    def test_playoffs_view_requires_confirmation_when_result_changes_qualifier(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        match = tie.first_leg
        match.home_score, match.away_score = 2, 0
        match.status = "finished"
        match.save()
        resolve_tie(tie)
        match.home_score, match.away_score = 0, 3
        match.save(update_fields=["home_score", "away_score"])
        organizer = User.objects.create_user(username="correction-organizer", password="secret", role="ORGANIZER")
        self.client.force_login(organizer)

        response = self.client.get(reverse("playoffs"), {"category": "seniors"})

        self.assertContains(response, "Confirma para recalcular los cruces posteriores")
        self.assertContains(response, f'action="{reverse("confirm_playoff_result_change", args=[tie.pk])}?category=seniors"')

    def test_settings_limit_classified_teams_to_two_through_sixty_four(self):
        self.settings.teams_classified = 6
        self.settings.full_clean()
        self.settings.teams_classified = 65
        with self.assertRaises(ValidationError):
            self.settings.full_clean()

    def test_thirty_three_teams_generate_a_round_of_sixty_four(self):
        teams = [
            Team.objects.create(name=f"Expansion Team {index}", coach="Coach", category="seniors")
            for index in range(9, 34)
        ]
        self.settings.teams_classified = 33
        self.settings.save(update_fields=["teams_classified"])

        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))

        first_round = playoff.ties.filter(round=PlayoffTie.ROUND_OF_64)
        self.assertEqual(first_round.count(), 32)
        self.assertEqual(first_round.filter(is_bye=True).count(), 31)
        self.assertEqual(PlayoffMatch.objects.filter(tie__in=first_round).count(), 1)
        self.assertEqual(playoff.ties.filter(round=PlayoffTie.ROUND_OF_32).count(), 16)
        self.assertEqual(len(teams), 25)

    def test_playoff_settings_are_independent_per_tournament(self):
        first_tournament = Tournament.objects.create(name="First League", season="2026", category="seniors")
        second_tournament = Tournament.objects.create(name="Second League", season="2026", category="seniors")

        first_settings = get_league_settings("seniors", tournament=first_tournament)
        second_settings = get_league_settings("seniors", tournament=second_tournament)
        first_settings.teams_classified = 4
        first_settings.save(update_fields=["teams_classified"])
        second_settings.teams_classified = 2
        second_settings.save(update_fields=["teams_classified"])

        self.assertNotEqual(first_settings.pk, second_settings.pk)
        self.assertEqual(get_teams_classified("seniors", tournament=first_tournament), 4)
        self.assertEqual(get_teams_classified("seniors", tournament=second_tournament), 2)
        self.assertEqual(get_teams_classified("seniors"), self.settings.teams_classified)


    def test_playoffs_view_renders_the_active_bracket(self):
        self.settings.playoffs_home_and_away = True
        self.settings.save(update_fields=["playoffs_home_and_away"])
        generate_playoff("seniors", date(2026, 6, 1), time(10, 0))

        response = self.client.get(reverse("playoffs"), {"category": "seniors"})

        self.assertContains(response, "Cuadro eliminatorio")
        self.assertContains(response, "Cuartos de final")
        self.assertContains(response, "IDA")
        self.assertContains(response, "Vuelta")
        self.assertContains(response, "Penales")
        self.assertContains(response, 'class="table app-table table-sm align-middle mb-0"')

    def test_playoffs_view_shows_leg_scores_instead_of_aggregate(self):
        self.settings.playoffs_home_and_away = True
        self.settings.save(update_fields=["playoffs_home_and_away"])
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        first_leg = tie.first_leg
        first_leg.home_score, first_leg.away_score = 4, 1
        first_leg.status = "finished"
        first_leg.save()
        second_leg = tie.second_leg
        second_leg.home_score, second_leg.away_score = 2, 0
        second_leg.status = "finished"
        second_leg.save()

        response = self.client.get(reverse("playoffs"), {"category": "seniors"})
        displayed_tie = response.context["rounds"][0]["ties"][0]

        self.assertEqual(displayed_tie["home_first_score"], 1)
        self.assertEqual(displayed_tie["away_first_score"], 4)
        self.assertEqual(displayed_tie["home_second_score"], 2)
        self.assertEqual(displayed_tie["away_second_score"], 0)
        self.assertNotIn("home_goals", displayed_tie)

    def test_playoffs_view_classifies_team_with_more_points_in_completed_tie(self):
        self.settings.playoffs_home_and_away = True
        self.settings.save(update_fields=["playoffs_home_and_away"])
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        first_leg = tie.first_leg
        second_leg = tie.second_leg
        first_leg.home_score, first_leg.away_score = 2, 0
        first_leg.status = "finished"
        first_leg.save()
        second_leg.home_score, second_leg.away_score = 0, 0
        second_leg.status = "finished"
        second_leg.save()

        response = self.client.get(reverse("playoffs"), {"category": "seniors"})

        self.assertEqual(response.status_code, 200)
        tie.refresh_from_db()
        self.assertEqual(tie.winner, tie.away_team)
        next_tie = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        next_tie.refresh_from_db()
        self.assertEqual(next_tie.home_team, tie.away_team)

    def test_playoffs_view_recovers_semifinal_slots_for_legacy_bracket(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        quarterfinals = list(playoff.ties.filter(round=PlayoffTie.QUARTERFINAL).order_by("position"))
        winners = []
        for tie in quarterfinals:
            tie.next_tie = None
            tie.next_slot = ""
            tie.save(update_fields=["next_tie", "next_slot"])
            match = tie.first_leg
            match.home_score, match.away_score = 2, 0
            match.status = "finished"
            match.save()
            winners.append(match.home_team)

        organizer = User.objects.create_user(username="organizer", password="secret", role="ORGANIZER")
        self.client.force_login(organizer)
        response = self.client.get(reverse("playoffs"), {"category": "seniors"})

        self.assertEqual(response.context["next_schedulable_round"], PlayoffTie.SEMIFINAL)
        self.assertContains(response, "Crear jornada")
        semifinal_one = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        semifinal_two = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=2)
        semifinal_one.refresh_from_db()
        semifinal_two.refresh_from_db()
        self.assertEqual((semifinal_one.home_team, semifinal_one.away_team), (winners[0], winners[3]))
        self.assertEqual((semifinal_two.home_team, semifinal_two.away_team), (winners[1], winners[2]))

    def test_playoffs_view_corrects_already_scheduled_unplayed_semifinal_fixtures(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        quarterfinals = list(playoff.ties.filter(round=PlayoffTie.QUARTERFINAL).order_by("position"))
        winners = []
        for tie in quarterfinals:
            tie.winner = tie.home_team
            tie.loser = tie.away_team
            tie.save(update_fields=["winner", "loser"])
            winners.append(tie.winner)

        semifinal_one = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=1)
        semifinal_two = playoff.ties.get(round=PlayoffTie.SEMIFINAL, position=2)
        # Mimic the old incorrect pairings, with matches already created but not played.
        semifinal_one.home_team, semifinal_one.away_team = winners[0], winners[1]
        semifinal_two.home_team, semifinal_two.away_team = winners[2], winners[3]
        semifinal_one.save(update_fields=["home_team", "away_team"])
        semifinal_two.save(update_fields=["home_team", "away_team"])
        match_day = MatchDay.objects.create(category="seniors", date=date(2026, 6, 20), description="Semifinal (ida)")
        first_one = Match.objects.create(
            home_team=winners[1], away_team=winners[0], match_day=match_day,
            date=match_day.date, time=time(15, 0), status="scheduled",
        )
        first_two = Match.objects.create(
            home_team=winners[3], away_team=winners[2], match_day=match_day,
            date=match_day.date, time=time(16, 0), status="scheduled",
        )
        PlayoffMatch.objects.create(tie=semifinal_one, match=first_one, leg=PlayoffMatch.FIRST)
        PlayoffMatch.objects.create(tie=semifinal_two, match=first_two, leg=PlayoffMatch.FIRST)

        response = self.client.get(reverse("playoffs"), {"category": "seniors"})

        self.assertEqual(response.status_code, 200)
        semifinal_one.refresh_from_db()
        semifinal_two.refresh_from_db()
        first_one.refresh_from_db()
        first_two.refresh_from_db()
        self.assertEqual((semifinal_one.home_team, semifinal_one.away_team), (winners[0], winners[3]))
        self.assertEqual((semifinal_two.home_team, semifinal_two.away_team), (winners[1], winners[2]))
        self.assertEqual((first_one.home_team, first_one.away_team), (winners[3], winners[0]))
        self.assertEqual((first_two.home_team, first_two.away_team), (winners[2], winners[1]))
        self.assertEqual(first_one.match_day, match_day)

    def test_organizer_can_create_semifinal_matchday_as_single_match(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        quarterfinals = playoff.ties.filter(round=PlayoffTie.QUARTERFINAL)
        for tie in quarterfinals:
            match = tie.first_leg
            match.home_score, match.away_score = 1, 0
            match.status = "finished"
            match.save()
            resolve_tie(tie)

        self.assertEqual(get_next_schedulable_round(playoff), PlayoffTie.SEMIFINAL)
        organizer = User.objects.create_user(username="organizer", password="secret", role="ORGANIZER")
        self.client.force_login(organizer)
        schedule_url = reverse("schedule_playoff_round", args=[PlayoffTie.SEMIFINAL])
        page = self.client.get(schedule_url, {"category": "seniors"})
        self.assertContains(page, "Crear jornada de semifinales")
        self.assertContains(page, "Ida y vuelta")
        self.assertContains(page, 'class="row g-3 mt-1 d-none"')
        self.assertContains(page, 'class="form-control bg-dark text-white border-secondary"')
        self.assertContains(page, 'class="form-select bg-dark text-white border-secondary"')
        self.assertContains(page, 'classList.toggle("d-none", !show)')

        response = self.client.post(
            schedule_url,
            {
                "match_date": "2026-06-15",
                "match_time": "15:00",
                "court": Match.COURT_2,
                "format": "single",
            },
            query_params={"category": "seniors"},
        )

        self.assertRedirects(response, f"{reverse('playoffs')}?category=seniors")
        semifinal_ties = playoff.ties.filter(round=PlayoffTie.SEMIFINAL)
        self.assertEqual(PlayoffMatch.objects.filter(tie__in=semifinal_ties, leg=PlayoffMatch.SINGLE).count(), 2)
        self.assertEqual(PlayoffMatch.objects.filter(tie__in=semifinal_ties).count(), 2)
        self.assertEqual(MatchDay.objects.filter(category="seniors", date=date(2026, 6, 15)).count(), 1)

    def test_organizer_can_schedule_next_round_home_and_away(self):
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        for tie in playoff.ties.filter(round=PlayoffTie.QUARTERFINAL):
            match = tie.first_leg
            match.home_score, match.away_score = 2, 0
            match.status = "finished"
            match.save()
            resolve_tie(tie)

        organizer = User.objects.create_user(username="organizer", password="secret", role="ORGANIZER")
        self.client.force_login(organizer)
        response = self.client.post(
            reverse("schedule_playoff_round", args=[PlayoffTie.SEMIFINAL]),
            {
                "match_date": "2026-06-15",
                "match_time": "15:00",
                "court": Match.COURT_1,
                "format": "home_and_away",
                "second_leg_date": "2026-06-22",
                "second_leg_time": "16:00",
            },
            query_params={"category": "seniors"},
        )

        self.assertRedirects(response, f"{reverse('playoffs')}?category=seniors")
        semifinal_ties = playoff.ties.filter(round=PlayoffTie.SEMIFINAL)
        self.assertEqual(PlayoffMatch.objects.filter(tie__in=semifinal_ties, leg=PlayoffMatch.FIRST).count(), 2)
        self.assertEqual(PlayoffMatch.objects.filter(tie__in=semifinal_ties, leg=PlayoffMatch.SECOND).count(), 2)
        self.assertEqual(MatchDay.objects.filter(category="seniors", date=date(2026, 6, 15)).count(), 1)
        self.assertEqual(MatchDay.objects.filter(category="seniors", date=date(2026, 6, 22)).count(), 1)

    def test_organizer_can_generate_playoffs_from_the_view(self):
        organizer = User.objects.create_user(username="organizer", password="secret", role="ORGANIZER")
        self.client.force_login(organizer)

        page = self.client.get(reverse("playoffs"), {"category": "seniors"})
        self.assertContains(page, 'class="row g-3 mt-2"')
        self.assertContains(page, 'class="form-select bg-dark text-white border-secondary"')
        self.assertContains(page, "Generar cuadro")

        response = self.client.post(
            reverse("generate_playoff"),
            {
                "match_date": "2026-06-01",
                "match_time": "10:00",
                "court": Match.COURT_1,
            },
            query_params={"category": "seniors"},
        )

        self.assertRedirects(response, f"{reverse('playoffs')}?category=seniors")
        self.assertEqual(PlayoffTie.objects.filter(playoff__category="seniors").count(), 8)

    def test_non_organizer_cannot_generate_playoffs(self):
        user = User.objects.create_user(username="player", password="secret", role="PLAYER")
        self.client.force_login(user)

        response = self.client.post(reverse("generate_playoff"), {"court": Match.COURT_1})

        self.assertEqual(response.status_code, 403)


class PlayoffSettingsViewTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="settings-owner", password="secret", role="ORGANIZER")
        self.other_organizer = User.objects.create_user(
            username="settings-other",
            password="secret",
            role="ORGANIZER",
        )
        self.tournament = Tournament.objects.create(name="Settings League", season="2026", category="seniors")
        self.tournament.organizers.add(self.organizer)
        self.legacy_settings = LeagueSettings.objects.create(
            category="seniors",
            teams_classified=8,
            playoffs_enabled=False,
        )
        self.url = f"{reverse('playoff_settings')}?category=seniors&tournament={self.tournament.pk}"

    def test_owner_sees_bootstrap_playoff_settings_form(self):
        self.client.force_login(self.organizer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="app-surface border rounded-3 p-3 p-md-4"')
        self.assertContains(response, 'class="row g-3"')
        self.assertContains(response, 'class="form-check-input"')
        self.assertContains(response, "Guardar reglas")

    def test_owner_can_save_tournament_specific_playoff_rules(self):
        self.client.force_login(self.organizer)

        response = self.client.post(
            self.url,
            {
                "teams_classified": "4",
                "playoffs_enabled": "on",
                "third_place_match": "on",
                "playoffs_home_and_away": "on",
                "penalties_on_aggregate_tie": "on",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('playoffs')}?category=seniors&tournament={self.tournament.pk}",
            fetch_redirect_response=False,
        )
        tournament_settings = LeagueSettings.objects.get(tournament=self.tournament)
        self.assertEqual(tournament_settings.teams_classified, 4)
        self.assertTrue(tournament_settings.playoffs_enabled)
        self.assertTrue(tournament_settings.playoffs_home_and_away)
        self.assertEqual(self.legacy_settings.teams_classified, 8)
        self.assertFalse(self.legacy_settings.playoffs_enabled)

    def test_settings_form_accepts_odd_team_count(self):
        settings = get_league_settings("seniors", tournament=self.tournament)
        form = PlayoffSettingsForm(data={"teams_classified": "5"}, instance=settings)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["teams_classified"], 5)

    def test_unassigned_organizer_cannot_change_playoff_settings(self):
        self.client.force_login(self.other_organizer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(LeagueSettings.objects.filter(tournament=self.tournament).exists())

    def test_active_playoff_locks_tournament_settings(self):
        settings = get_league_settings("seniors", tournament=self.tournament)
        settings.playoffs_enabled = True
        settings.save(update_fields=["playoffs_enabled"])
        Playoff.objects.create(category="seniors", tournament=self.tournament, settings=settings)
        self.client.force_login(self.organizer)

        response = self.client.post(self.url, {"teams_classified": "4", "playoffs_enabled": "on"})

        self.assertRedirects(
            response,
            f"{reverse('playoffs')}?category=seniors&tournament={self.tournament.pk}",
            fetch_redirect_response=False,
        )
        settings.refresh_from_db()
        self.assertEqual(settings.teams_classified, 8)