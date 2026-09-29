from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.matches.models import Match
from apps.playoffs.models import LeagueSettings, PlayoffMatch, PlayoffTie
from apps.playoffs.services import (
    generate_playoff,
    get_next_schedulable_round,
    get_tie_points,
    record_penalty_result,
    resolve_tie,
)
from apps.teams.models import Team
from apps.tournaments.models import MatchDay
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
        self.assertContains(bracket_response, "Empate en puntos: 3 - 3")
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

    def test_points_tie_requires_penalties_even_when_aggregate_goals_are_not_tied(self):
        self.settings.playoffs_home_and_away = True
        self.settings.save(update_fields=["playoffs_home_and_away"])
        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))
        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        first_leg = tie.first_leg
        second_leg = tie.second_leg

        # The tie's home team wins the first leg 5-0; the away team wins the return 1-0.
        first_leg.home_score, first_leg.away_score = 0, 5
        first_leg.status = "finished"
        first_leg.save()
        second_leg.home_score, second_leg.away_score = 0, 1
        second_leg.status = "finished"
        second_leg.save()

        self.assertEqual(get_tie_points(tie), (3, 3))
        with self.assertRaises(ValidationError):
            resolve_tie(tie)

        resolved_tie = record_penalty_result(tie, 5, 4)

        self.assertEqual(resolved_tie.winner, tie.home_team)

    def test_settings_require_a_power_of_two(self):
        self.settings.teams_classified = 6
        with self.assertRaises(ValidationError):
            self.settings.full_clean()

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