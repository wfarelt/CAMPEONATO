from datetime import date, time

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.matches.models import Match
from apps.teams.models import Player, Team
from apps.tournaments.forms import MatchDayForm, MatchForm, get_match_formset_class
from apps.tournaments.models import MatchDay, Tournament, TournamentPlayer, TournamentTeam
from apps.tournaments.services import (
    initialize_tournament_rosters,
    recommend_matches_for_matchday,
    validate_matchday_teams,
)
from apps.users.models import User


class MatchRecommendationTests(TestCase):
    def setUp(self):
        self.team_a = Team.objects.create(name="Team A", coach="Coach A", category="seniors")
        self.team_b = Team.objects.create(name="Team B", coach="Coach B", category="seniors")
        self.team_c = Team.objects.create(name="Team C", coach="Coach C", category="seniors")
        self.team_d = Team.objects.create(name="Team D", coach="Coach D", category="seniors")

    def test_recommendation_uses_only_available_teams(self):
        self.team_d.is_available_for_matchday = False
        self.team_d.save(update_fields=["is_available_for_matchday"])

        recommendation = recommend_matches_for_matchday("seniors", 2)
        recommendations = recommendation["matches"]

        involved_teams = {match["home_team"] for match in recommendations}
        involved_teams.update({match["away_team"] for match in recommendations})

        self.assertNotIn(self.team_d.id, involved_teams)

    def test_recommendation_prioritizes_teams_with_fewer_matches(self):
        Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            date=date(2026, 5, 1),
            time=time(10, 0),
            court=Match.COURT_1,
            status="finished",
            home_score=1,
            away_score=0,
        )
        Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_c,
            date=date(2026, 5, 2),
            time=time(10, 0),
            court=Match.COURT_1,
            status="finished",
            home_score=1,
            away_score=0,
        )

        recommendation = recommend_matches_for_matchday("seniors", 1)
        recommendations = recommendation["matches"]

        self.assertEqual(len(recommendations), 1)
        first = recommendations[0]
        involved_teams = {first["home_team"], first["away_team"]}
        self.assertIn(self.team_d.id, involved_teams)

    def test_recommendation_avoids_repeated_historical_pairings(self):
        Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            date=date(2026, 5, 1),
            time=time(10, 0),
            court=Match.COURT_1,
            status="finished",
        )

        recommendation = recommend_matches_for_matchday("seniors", 2)

        self.assertTrue(recommendation["possible"])
        matches = recommendation["matches"]
        self.assertEqual(len(matches), 2)
        pairs = {frozenset((m["home_team"], m["away_team"])) for m in matches}
        self.assertNotIn(frozenset((self.team_a.id, self.team_b.id)), pairs)

    def test_recommendation_avoids_reusing_teams_in_same_round(self):
        recommendation = recommend_matches_for_matchday("seniors", 3)

        self.assertFalse(recommendation["possible"])
        self.assertEqual(recommendation["matches"], [])
        self.assertEqual(recommendation["max_possible"], 2)
        self.assertIn("2", recommendation["message"])

    def test_recommendation_detects_impossible_due_to_history(self):
        Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            date=date(2026, 5, 1),
            time=time(10, 0),
            court=Match.COURT_1,
            status="finished",
        )
        Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_c,
            date=date(2026, 5, 2),
            time=time(10, 0),
            court=Match.COURT_1,
            status="finished",
        )
        Match.objects.create(
            home_team=self.team_b,
            away_team=self.team_c,
            date=date(2026, 5, 3),
            time=time(10, 0),
            court=Match.COURT_1,
            status="finished",
        )

        recommendation = recommend_matches_for_matchday("seniors", 2)

        self.assertFalse(recommendation["possible"])
        self.assertEqual(recommendation["max_possible"], 1)
        self.assertEqual(recommendation["matches"], [])

    def test_dynamic_formset_renders_requested_initial_matches(self):
        initial_matches = [
            {"home_team": self.team_a.id, "away_team": self.team_b.id},
            {"home_team": self.team_c.id, "away_team": self.team_d.id},
        ]
        formset_class = get_match_formset_class(extra=len(initial_matches))
        formset = formset_class(initial=initial_matches)

        self.assertGreaterEqual(formset.total_form_count(), 2)

    def test_matchday_formset_rejects_reusing_a_team(self):
        formset_class = get_match_formset_class(extra=2)
        formset = formset_class(
            data={
                "matches-TOTAL_FORMS": "2",
                "matches-INITIAL_FORMS": "0",
                "matches-MIN_NUM_FORMS": "0",
                "matches-MAX_NUM_FORMS": "1000",
                "matches-0-home_team": str(self.team_a.pk),
                "matches-0-away_team": str(self.team_b.pk),
                "matches-0-court": str(Match.COURT_1),
                "matches-0-time": "10:00",
                "matches-1-home_team": str(self.team_a.pk),
                "matches-1-away_team": str(self.team_c.pk),
                "matches-1-court": str(Match.COURT_2),
                "matches-1-time": "11:00",
            },
            form_kwargs={"category": "seniors"},
        )

        self.assertFalse(formset.is_valid())
        self.assertIn(
            "Un equipo no puede aparecer en más de un partido de la misma jornada.",
            formset.non_form_errors(),
        )
class TournamentModelTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Season Team", coach="Coach", category="seniors")
        self.tournament = Tournament.objects.create(
            name="Liga Seniors",
            season="2026",
            category="seniors",
        )

    def test_tournament_team_membership_requires_matching_category(self):
        self.team.category = "super_seniors"
        self.team.save(update_fields=["category"])
        membership = TournamentTeam(tournament=self.tournament, team=self.team)

        with self.assertRaises(ValidationError):
            membership.full_clean()

    def test_tournament_team_membership_is_unique(self):
        TournamentTeam.objects.create(tournament=self.tournament, team=self.team)

        with self.assertRaises(IntegrityError), transaction.atomic():
            TournamentTeam.objects.create(tournament=self.tournament, team=self.team)

    def test_matchday_requires_tournament_category_to_match(self):
        tournament = Tournament.objects.create(
            name="Liga Super Seniors",
            season="2026",
            category="super_seniors",
        )
        matchday = MatchDay(
            tournament=tournament,
            category="seniors",
            date=date(2026, 6, 1),
        )

        with self.assertRaises(ValidationError):
            matchday.full_clean()

    def test_service_rejects_repeated_team_in_matchday(self):
        matchday = MatchDay(
            tournament=self.tournament,
            category="seniors",
            date=date(2026, 6, 1),
        )

        with self.assertRaises(ValidationError):
            validate_matchday_teams(matchday, [self.team.pk, self.team.pk])

    def test_service_rejects_team_not_enrolled_in_matchday_tournament(self):
        unregistered_team = Team.objects.create(name="Unregistered", coach="Coach", category="seniors")
        matchday = MatchDay(
            tournament=self.tournament,
            category="seniors",
            date=date(2026, 6, 1),
        )

        with self.assertRaises(ValidationError):
            validate_matchday_teams(matchday, [self.team.pk, unregistered_team.pk])

    def test_matchday_form_limits_tournament_choices_to_category(self):
        other_tournament = Tournament.objects.create(
            name="Liga Super Seniors",
            season="2026",
            category="super_seniors",
        )

        form = MatchDayForm(initial={"category": "seniors"})

        self.assertQuerySetEqual(
            form.fields["tournament"].queryset,
            [self.tournament],
        )
        self.assertNotIn(other_tournament, form.fields["tournament"].queryset)

    def test_match_form_limits_teams_to_tournament_members(self):
        other_team = Team.objects.create(name="Outside Team", coach="Coach", category="seniors")
        self.tournament.teams.add(self.team)
        form = MatchForm(category="seniors", tournament=self.tournament)

        self.assertIn(self.team, form.fields["home_team"].queryset)
        self.assertNotIn(other_team, form.fields["home_team"].queryset)

    def test_recommendations_only_consider_matches_in_selected_tournament(self):
        other_team = Team.objects.create(name="Other Season Team", coach="Coach", category="seniors")
        other_tournament = Tournament.objects.create(
            name="Otra liga",
            season="2025",
            category="seniors",
        )
        self.tournament.teams.add(self.team)
        self.tournament.teams.add(other_team)
        other_tournament.teams.add(self.team)
        other_tournament.teams.add(other_team)
        matchday = MatchDay.objects.create(
            tournament=other_tournament,
            category="seniors",
            date=date(2025, 6, 1),
        )
        Match.objects.create(
            match_day=matchday,
            home_team=self.team,
            away_team=other_team,
            date=matchday.date,
            time=time(10, 0),
        )

        recommendation = recommend_matches_for_matchday("seniors", 1, tournament=self.tournament)

        self.assertTrue(recommendation["possible"])
        self.assertEqual(len(recommendation["matches"]), 1)

    def test_new_tournament_copies_only_the_previous_active_roster(self):
        returning_player = Player.objects.create(team=self.team, name="Returning", position="FW")
        leaving_player = Player.objects.create(team=self.team, name="Leaving", position="DF")
        self.tournament.teams.add(self.team)
        initialize_tournament_rosters(self.tournament, [self.team])
        TournamentPlayer.objects.filter(tournament_team__tournament=self.tournament, player=leaving_player).update(
            is_active=False
        )

        new_tournament = Tournament.objects.create(name="Liga Seniors", season="2027", category="seniors")
        new_tournament.teams.add(self.team)
        initialize_tournament_rosters(new_tournament, [self.team])

        new_roster = TournamentPlayer.objects.filter(tournament_team__tournament=new_tournament)
        self.assertQuerySetEqual(new_roster.values_list("player_id", flat=True), [returning_player.pk])


class TournamentManagementViewsTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="season-organizer", password="secret", role="ORGANIZER")
        self.player = User.objects.create_user(username="season-player", password="secret", role="PLAYER")
        self.team = Team.objects.create(name="Enrolled Team", coach="Coach", category="seniors")

    def test_organizer_can_create_tournament_and_enroll_teams(self):
        player = Player.objects.create(team=self.team, name="Returning Player", position="FW")
        self.client.force_login(self.organizer)

        form_page = self.client.get(f"{reverse('tournament_create')}?category=seniors")
        self.assertEqual(form_page.status_code, 200)
        self.assertContains(form_page, 'class="app-surface border rounded-3 p-3 p-md-4"')
        self.assertContains(form_page, 'class="row g-3"')
        self.assertContains(form_page, 'class="form-select"')

        response = self.client.post(
            f"{reverse('tournament_create')}?category=seniors",
            {
                "name": "Liga Apertura",
                "season": "2026",
                "category": "seniors",
                "status": Tournament.SETUP,
                "teams": [str(self.team.pk)],
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('tournaments_list')}?category=seniors",
            fetch_redirect_response=False,
        )
        tournament = Tournament.objects.get(name="Liga Apertura", season="2026")
        self.assertEqual(list(tournament.teams.all()), [self.team])
        self.assertTrue(tournament.organizers.filter(pk=self.organizer.pk).exists())
        self.assertTrue(
            TournamentPlayer.objects.filter(
                tournament_team__tournament=tournament,
                player=player,
                is_active=True,
            ).exists()
        )

    def test_matchday_wizard_uses_bootstrap_layout_for_first_two_steps(self):
        self.client.force_login(self.organizer)

        first_step = self.client.get(reverse("create_matchday"), {"category": "seniors"})

        self.assertEqual(first_step.status_code, 200)
        self.assertContains(first_step, "class=\"row row-cols-1 row-cols-sm-3 g-2 mb-4\"")
        self.assertContains(first_step, "Registrar jornada")

        next_step = self.client.post(
            f"{reverse('create_matchday')}?category=seniors",
            {
                "step": "1",
                "category": "seniors",
                "date": "2026-06-15",
                "description": "Fecha de prueba",
                "is_visible": "on",
            },
        )

        self.assertEqual(next_step.status_code, 302)
        second_step = self.client.get(next_step.url)
        self.assertEqual(second_step.status_code, 200)
        self.assertContains(second_step, "class=\"row g-3 align-items-end\"")
        self.assertContains(second_step, "Añadir partido")

    def test_matchday_list_renders_bootstrap_empty_state(self):
        self.client.force_login(self.organizer)

        response = self.client.get(reverse("matchdays_list"), {"category": "seniors"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "app-empty-state border rounded-3")
        self.assertContains(response, "Crear la primera jornada")

    def test_matchday_list_renders_bootstrap_table(self):
        self.client.force_login(self.organizer)
        matchday = MatchDay.objects.create(category="seniors", date=date(2026, 6, 15), description="Primera fecha")

        response = self.client.get(reverse("matchdays_list"), {"category": "seniors"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "table table-hover align-middle app-table mb-0")
        self.assertContains(response, "Primera fecha")
        self.assertContains(response, reverse("matchday_detail", kwargs={"matchday_slug": matchday.slug}))

    def test_matchday_detail_renders_bootstrap_summary(self):
        self.client.force_login(self.organizer)
        matchday = MatchDay.objects.create(category="seniors", date=date(2026, 6, 15), description="Primera fecha")

        response = self.client.get(
            reverse("matchday_detail", kwargs={"matchday_slug": matchday.slug}),
            {"category": "seniors"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "row row-cols-2 row-cols-sm-3 g-3 mb-4")
        self.assertContains(response, "app-surface border rounded-3 overflow-hidden")
        self.assertContains(response, "No hay partidos registrados en esta jornada.")

    def test_non_organizer_cannot_manage_tournaments(self):
        self.client.force_login(self.player)

        response = self.client.get(reverse("tournaments_list"), {"category": "seniors"})

        self.assertEqual(response.status_code, 403)

    def test_organizer_can_view_list_and_edit_team_membership(self):
        tournament = Tournament.objects.create(name="Liga Invierno", season="2026", category="seniors")
        tournament.organizers.add(self.organizer)
        tournament.teams.add(self.team)
        replacement = Team.objects.create(name="Replacement Team", coach="Coach", category="seniors")
        self.client.force_login(self.organizer)

        list_response = self.client.get(reverse("tournaments_list"), {"category": "seniors"})
        edit_response = self.client.get(
            reverse("tournament_edit", args=[tournament.pk]),
            {"category": "seniors"},
        )

        self.assertContains(list_response, "Liga Invierno")
        self.assertContains(edit_response, "Equipos participantes")
        self.assertContains(edit_response, 'class="form-select"')
        update_response = self.client.post(
            f"{reverse('tournament_edit', args=[tournament.pk])}?category=seniors",
            {
                "name": tournament.name,
                "season": tournament.season,
                "category": tournament.category,
                "status": tournament.status,
                "teams": [str(replacement.pk)],
            },
        )

        self.assertRedirects(
            update_response,
            f"{reverse('tournaments_list')}?category=seniors",
            fetch_redirect_response=False,
        )
        self.assertEqual(list(tournament.teams.all()), [replacement])

    def test_organizer_cannot_edit_another_organizers_tournament(self):
        owner = User.objects.create_user(username="other-organizer", password="secret", role="ORGANIZER")
        tournament = Tournament.objects.create(name="Liga Privada", season="2026", category="seniors")
        tournament.organizers.add(owner)
        self.client.force_login(self.organizer)

        response = self.client.get(
            reverse("tournament_edit", args=[tournament.pk]),
            {"category": "seniors"},
        )

        self.assertEqual(response.status_code, 404)

    def test_matchday_form_only_offers_tournaments_assigned_to_organizer(self):
        assigned = Tournament.objects.create(name="Assigned", season="2026", category="seniors")
        assigned.organizers.add(self.organizer)
        unassigned = Tournament.objects.create(name="Unassigned", season="2025", category="seniors")

        form = MatchDayForm(initial={"category": "seniors"}, user=self.organizer)

        self.assertIn(assigned, form.fields["tournament"].queryset)
        self.assertNotIn(unassigned, form.fields["tournament"].queryset)

    def test_organizer_cannot_create_matchday_for_another_organizers_tournament(self):
        owner = User.objects.create_user(username="matchday-owner", password="secret", role="ORGANIZER")
        tournament = Tournament.objects.create(name="Owner Season", season="2026", category="seniors")
        tournament.organizers.add(owner)
        self.client.force_login(self.organizer)

        response = self.client.get(
            reverse("create_matchday"),
            {"category": "seniors", "tournament": tournament.pk},
        )

        self.assertEqual(response.status_code, 403)

    def test_deleting_team_in_tournament_only_removes_its_membership(self):
        tournament = Tournament.objects.create(name="Team Season", season="2026", category="seniors")
        tournament.organizers.add(self.organizer)
        tournament.teams.add(self.team)
        other_tournament = Tournament.objects.create(name="Other Team Season", season="2025", category="seniors")
        other_tournament.teams.add(self.team)
        self.client.force_login(self.organizer)

        response = self.client.post(
            f"{reverse('team_delete', args=[self.team.slug])}?category=seniors&tournament={tournament.pk}"
        )

        self.assertRedirects(
            response,
            f"{reverse('teams')}?category=seniors&tournament={tournament.pk}",
            fetch_redirect_response=False,
        )
        self.assertTrue(Team.objects.filter(pk=self.team.pk).exists())
        self.assertFalse(tournament.teams.filter(pk=self.team.pk).exists())
        self.assertTrue(other_tournament.teams.filter(pk=self.team.pk).exists())
