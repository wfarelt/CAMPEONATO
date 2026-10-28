from datetime import date, time

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.matches.models import Match
from apps.teams.models import Team
from apps.tournaments.forms import get_match_formset_class
from apps.tournaments.models import MatchDay, Tournament, TournamentTeam
from apps.tournaments.services import recommend_matches_for_matchday


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
