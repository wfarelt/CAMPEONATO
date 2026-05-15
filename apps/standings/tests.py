from datetime import date, time

from django.test import TestCase

from apps.matches.models import Match, PointsAdjustment
from apps.standings.services import build_standings
from apps.teams.models import Team


class StandingsServiceTests(TestCase):
    def setUp(self):
        self.team_a = Team.objects.create(name="Alpha FC", coach="Coach A", category="seniors")
        self.team_b = Team.objects.create(name="Beta FC", coach="Coach B", category="seniors")
        self.team_c = Team.objects.create(name="Gamma FC", coach="Coach C", category="seniors")
        self.super_a = Team.objects.create(name="Master FC", coach="Coach M", category="super_seniors")
        self.super_b = Team.objects.create(name="Veteranos FC", coach="Coach V", category="super_seniors")

        Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            home_score=2,
            away_score=1,
            date=date(2026, 5, 10),
            time=time(15, 0),
            status="finished",
        )
        Match.objects.create(
            home_team=self.team_c,
            away_team=self.team_a,
            home_score=0,
            away_score=0,
            date=date(2026, 5, 11),
            time=time(16, 0),
            status="finished",
        )
        Match.objects.create(
            home_team=self.super_a,
            away_team=self.super_b,
            home_score=1,
            away_score=1,
            date=date(2026, 5, 9),
            time=time(12, 0),
            status="finished",
        )
        PointsAdjustment.objects.create(team=self.team_a, points=1, reason="Bonus")

    def test_build_standings_applies_adjustments_and_sorting(self):
        standings = build_standings(category="seniors", include_adjustments=True)

        self.assertEqual(standings[0]["team"], "Alpha FC")
        self.assertEqual(standings[0]["points"], 5)
        self.assertEqual(standings[0]["won"], 1)
        self.assertEqual(standings[0]["drawn"], 1)
        self.assertEqual(standings[0]["goal_difference"], 1)

    def test_build_standings_can_skip_adjustments(self):
        standings = build_standings(category="seniors", include_adjustments=False)
        alpha = next(item for item in standings if item["team"] == "Alpha FC")

        self.assertEqual(alpha["points"], 4)

    def test_build_standings_filters_by_category(self):
        standings = build_standings(category="super_seniors", include_adjustments=False)

        self.assertEqual(len(standings), 2)
        self.assertEqual({item["team"] for item in standings}, {"Master FC", "Veteranos FC"})
