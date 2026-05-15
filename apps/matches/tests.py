from datetime import date, time

from django.test import TestCase

from apps.matches.models import Match
from apps.matches.services import build_home_context, build_matches_context
from apps.teams.models import Team
from apps.tournaments.models import MatchDay


class MatchServicesTests(TestCase):
    def setUp(self):
        self.team_a = Team.objects.create(name="Alpha FC", coach="Coach A", category="seniors")
        self.team_b = Team.objects.create(name="Beta FC", coach="Coach B", category="seniors")
        self.team_c = Team.objects.create(name="Gamma FC", coach="Coach C", category="seniors")
        self.team_d = Team.objects.create(name="Delta FC", coach="Coach D", category="seniors")
        self.super_home = Team.objects.create(name="Master FC", coach="Coach M", category="super_seniors")
        self.super_away = Team.objects.create(name="Veteranos FC", coach="Coach V", category="super_seniors")

        self.matchday = MatchDay.objects.create(date=date(2026, 5, 12), description="Fecha 1", category="seniors")
        self.finished_match = Match.objects.create(
            match_day=self.matchday,
            home_team=self.team_a,
            away_team=self.team_b,
            home_score=3,
            away_score=1,
            date=self.matchday.date,
            time=time(14, 0),
            status="finished",
        )
        self.scheduled_match = Match.objects.create(
            match_day=self.matchday,
            home_team=self.team_c,
            away_team=self.team_d,
            home_score=0,
            away_score=0,
            date=self.matchday.date,
            time=time(18, 30),
            status="scheduled",
        )

        super_matchday = MatchDay.objects.create(date=date(2026, 5, 11), description="Super Fecha", category="super_seniors")
        Match.objects.create(
            match_day=super_matchday,
            home_team=self.super_home,
            away_team=self.super_away,
            home_score=1,
            away_score=0,
            date=super_matchday.date,
            time=time(13, 0),
            status="finished",
        )

    def test_build_home_context_uses_latest_matchday(self):
        context = build_home_context(category="seniors")

        self.assertEqual(context["timeline_title"], "Fecha 1")
        self.assertEqual(len(context["timeline_matches"]), 2)
        self.assertEqual(context["featured_match"]["home_team"], "Alpha FC")
        self.assertTrue(context["featured_match"]["is_finished"])

    def test_build_matches_context_includes_pending_and_finished(self):
        context = build_matches_context(category="seniors")

        self.assertEqual(len(context["matches_pending"]), 1)
        self.assertEqual(context["matches_pending"][0]["home_team"], "Gamma FC")
        self.assertEqual(list(context["matches_finished"]), [self.finished_match])
        self.assertEqual(context["matches_pending"][0]["home_team_last_results"], [])

    def test_build_matches_context_excludes_other_category(self):
        context = build_matches_context(category="super_seniors")

        self.assertEqual(len(context["matches_pending"]), 0)
        self.assertEqual(len(list(context["matches_finished"])), 1)
        self.assertEqual(list(context["matches_finished"])[0].home_team.name, "Master FC")
