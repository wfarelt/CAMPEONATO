from datetime import date, time
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase

from apps.matches.models import Match, MatchEvent
from apps.matches.services import build_home_context, build_matches_context, build_statistics_context
from apps.playoffs.models import LeagueSettings, Playoff, PlayoffMatch, PlayoffTie
from apps.teams.models import Player, Team
from apps.tournaments.models import MatchDay
from apps.users.models import User


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
        LeagueSettings.objects.create(category="seniors", teams_classified=4)
        context = build_home_context(category="seniors")

        self.assertEqual(context["timeline_title"], "Fecha 1")
        self.assertEqual(len(context["timeline_matches"]), 2)
        self.assertEqual(context["featured_match"]["home_team"], "Alpha FC")
        self.assertTrue(context["featured_match"]["is_finished"])
        self.assertEqual(context["teams_classified"], 4)

    def test_home_playoff_context_shows_only_current_round(self):
        settings = LeagueSettings.objects.create(category="seniors", teams_classified=4, playoffs_enabled=True)
        playoff = Playoff.objects.create(category="seniors", settings=settings)
        semifinal_one = PlayoffTie.objects.create(
            playoff=playoff,
            round=PlayoffTie.SEMIFINAL,
            position=1,
            home_team=self.team_a,
            away_team=self.team_b,
        )
        semifinal_two = PlayoffTie.objects.create(
            playoff=playoff,
            round=PlayoffTie.SEMIFINAL,
            position=2,
            home_team=self.team_c,
            away_team=self.team_d,
        )
        PlayoffTie.objects.create(playoff=playoff, round=PlayoffTie.FINAL, position=1)

        context = build_home_context(category="seniors")

        self.assertEqual([round_data["label"] for round_data in context["playoff_rounds"]], ["Semifinal"])
        semifinal_one.winner = self.team_a
        semifinal_one.loser = self.team_b
        semifinal_one.save(update_fields=["winner", "loser"])
        semifinal_two.winner = self.team_c
        semifinal_two.loser = self.team_d
        semifinal_two.save(update_fields=["winner", "loser"])

        context = build_home_context(category="seniors")

        self.assertEqual([round_data["label"] for round_data in context["playoff_rounds"]], ["Final"])

    def test_home_playoff_context_includes_ida_vuelta_and_penalty_scores(self):
        settings = LeagueSettings.objects.create(category="seniors", teams_classified=4, playoffs_enabled=True)
        playoff = Playoff.objects.create(category="seniors", settings=settings)
        tie = PlayoffTie.objects.create(
            playoff=playoff,
            round=PlayoffTie.SEMIFINAL,
            position=1,
            home_team=self.team_a,
            away_team=self.team_b,
            decided_by_penalties=True,
            home_penalties=5,
            away_penalties=4,
        )
        first_leg = Match.objects.create(
            home_team=self.team_b,
            away_team=self.team_a,
            home_score=1,
            away_score=0,
            date=date(2026, 5, 20),
            time=time(14, 0),
            status="finished",
        )
        second_leg = Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            home_score=2,
            away_score=0,
            date=date(2026, 5, 27),
            time=time(14, 0),
            status="finished",
        )
        PlayoffMatch.objects.create(tie=tie, match=first_leg, leg=PlayoffMatch.FIRST)
        PlayoffMatch.objects.create(tie=tie, match=second_leg, leg=PlayoffMatch.SECOND)

        context = build_home_context(category="seniors")
        home_tie = context["playoff_rounds"][0]["ties"][0]

        self.assertEqual(home_tie["first_leg_label"], "IDA")
        self.assertEqual((home_tie["home_first_score"], home_tie["away_first_score"]), (0, 1))
        self.assertEqual((home_tie["home_second_score"], home_tie["away_second_score"]), (2, 0))
        self.assertEqual((home_tie["home_points"], home_tie["away_points"]), (3, 3))

        response = self.client.get("/", {"category": "seniors"})
        self.assertContains(response, "IDA")
        self.assertContains(response, "VUELTA")
        self.assertContains(response, "PENALES")
        self.assertContains(response, "PUNTOS DE LA LLAVE: 3 - 3")

    def test_home_playoff_context_matches_leg_scores_to_the_tie_teams(self):
        settings = LeagueSettings.objects.create(category="seniors", teams_classified=4, playoffs_enabled=True)
        playoff = Playoff.objects.create(category="seniors", settings=settings)
        first_tie = PlayoffTie.objects.create(
            playoff=playoff,
            round=PlayoffTie.SEMIFINAL,
            position=1,
            home_team=self.team_a,
            away_team=self.team_b,
        )
        second_tie = PlayoffTie.objects.create(
            playoff=playoff,
            round=PlayoffTie.SEMIFINAL,
            position=2,
            home_team=self.team_c,
            away_team=self.team_d,
        )
        first_tie_match = Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            home_score=3,
            away_score=1,
            date=date(2026, 5, 20),
            time=time(14, 0),
            status="finished",
        )
        second_tie_match = Match.objects.create(
            home_team=self.team_c,
            away_team=self.team_d,
            home_score=0,
            away_score=2,
            date=date(2026, 5, 20),
            time=time(15, 0),
            status="finished",
        )
        # Reproduce stale tie-to-match links: each first leg is attached to the other tie.
        PlayoffMatch.objects.create(tie=first_tie, match=second_tie_match, leg=PlayoffMatch.FIRST)
        PlayoffMatch.objects.create(tie=second_tie, match=first_tie_match, leg=PlayoffMatch.FIRST)

        context = build_home_context(category="seniors")
        first_tie_data = next(
            tie for tie in context["playoff_rounds"][0]["ties"] if tie["home_team"] == self.team_a.name
        )

        self.assertEqual((first_tie_data["home_first_score"], first_tie_data["away_first_score"]), (3, 1))
        self.assertEqual((first_tie_data["home_points"], first_tie_data["away_points"]), (3, 0))

    def test_finishing_a_tied_playoff_match_redirects_to_penalty_entry(self):
        settings = LeagueSettings.objects.create(category="seniors", playoffs_enabled=True)
        playoff = Playoff.objects.create(category="seniors", settings=settings)
        tie = PlayoffTie.objects.create(
            playoff=playoff,
            round=PlayoffTie.SEMIFINAL,
            position=1,
            home_team=self.team_a,
            away_team=self.team_b,
        )
        match = Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            date=date(2026, 5, 20),
            time=time(14, 0),
            status="scheduled",
        )
        PlayoffMatch.objects.create(tie=tie, match=match, leg=PlayoffMatch.SINGLE)
        organizer = User.objects.create_user(username="organizer", password="secret", role="ORGANIZER")
        self.client.force_login(organizer)

        response = self.client.post(
            f"/partidos/{match.slug}/resultado/",
            {
                "action": "save_match",
                "home_score": 1,
                "away_score": 1,
                "status": "finished",
                "court": match.court,
                "date": match.date.isoformat(),
                "time": match.time.strftime("%H:%M"),
            },
        )

        self.assertRedirects(response, "/playoffs/?category=seniors", fetch_redirect_response=False)
        playoffs_response = self.client.get("/playoffs/?category=seniors")
        self.assertContains(playoffs_response, "Empate en puntos: 1 - 1")
        self.assertContains(playoffs_response, "name=\"home_penalties\"")

    def test_finishing_a_decisive_playoff_match_advances_winner_automatically(self):
        settings = LeagueSettings.objects.create(category="seniors", playoffs_enabled=True)
        playoff = Playoff.objects.create(category="seniors", settings=settings)
        final_tie = PlayoffTie.objects.create(playoff=playoff, round=PlayoffTie.FINAL, position=1)
        tie = PlayoffTie.objects.create(
            playoff=playoff,
            round=PlayoffTie.SEMIFINAL,
            position=1,
            home_team=self.team_a,
            away_team=self.team_b,
            next_tie=final_tie,
            next_slot="home",
        )
        match = Match.objects.create(
            home_team=self.team_a,
            away_team=self.team_b,
            date=date(2026, 5, 20),
            time=time(14, 0),
            status="scheduled",
        )
        PlayoffMatch.objects.create(tie=tie, match=match, leg=PlayoffMatch.SINGLE)
        organizer = User.objects.create_user(username="organizer", password="secret", role="ORGANIZER")
        self.client.force_login(organizer)

        response = self.client.post(
            f"/partidos/{match.slug}/resultado/",
            {
                "action": "save_match",
                "home_score": 2,
                "away_score": 0,
                "status": "finished",
                "court": match.court,
                "date": match.date.isoformat(),
                "time": match.time.strftime("%H:%M"),
            },
        )

        self.assertRedirects(response, "/playoffs/?category=seniors", fetch_redirect_response=False)
        tie.refresh_from_db()
        final_tie.refresh_from_db()
        self.assertEqual(tie.winner, self.team_a)
        self.assertEqual(final_tie.home_team, self.team_a)

    def test_build_home_context_uses_next_scheduled_matchday(self):
        self.scheduled_match.status = "finished"
        self.scheduled_match.save(update_fields=["status"])
        next_matchday = MatchDay.objects.create(date=date(2026, 5, 19), description="Fecha 2", category="seniors")
        Match.objects.create(
            match_day=next_matchday,
            home_team=self.team_a,
            away_team=self.team_c,
            date=next_matchday.date,
            time=time(16, 0),
            status="scheduled",
        )

        context = build_home_context(category="seniors")

        self.assertEqual(context["timeline_title"], "Fecha 2")
        self.assertEqual(len(context["timeline_matches"]), 1)
        self.assertEqual(context["timeline_matches"][0]["home_team"], "Alpha FC")

    def test_build_matches_context_includes_pending_and_finished(self):
        context = build_matches_context(category="seniors")

        self.assertEqual(len(context["matches_pending"]), 1)
        self.assertEqual(context["matches_pending"][0]["home_team"], "Gamma FC")
        self.assertEqual(list(context["matches_finished"]), [self.finished_match])
        self.assertEqual(context["matches_pending"][0]["home_team_last_results"], [])

    def test_build_matches_context_orders_pending_by_court_and_time(self):
        second_match = Match.objects.create(
            match_day=self.matchday,
            home_team=self.team_a,
            away_team=self.team_d,
            home_score=0,
            away_score=0,
            court=Match.COURT_1,
            date=self.matchday.date,
            time=time(10, 0),
            status="scheduled",
        )
        Match.objects.filter(pk=self.scheduled_match.pk).update(court=Match.COURT_2)

        context = build_matches_context(category="seniors")

        self.assertEqual([match["slug"] for match in context["matches_pending"]], [second_match.slug, self.scheduled_match.slug])

    def test_build_matches_context_excludes_other_category(self):
        context = build_matches_context(category="super_seniors")

        self.assertEqual(len(context["matches_pending"]), 0)
        self.assertEqual(len(list(context["matches_finished"])), 1)
        self.assertEqual(list(context["matches_finished"])[0].home_team.name, "Master FC")

    def test_build_statistics_context_returns_top_scorers(self):
        Player.objects.create(team=self.team_a, name="Striker A", number=9, position="FW", goals_scored=6)
        Player.objects.create(team=self.team_b, name="Striker B", number=10, position="FW", goals_scored=8)
        Player.objects.create(team=self.team_c, name="Striker C", number=11, position="FW", goals_scored=3)

        context = build_statistics_context(category="seniors")

        self.assertEqual(len(context["top_scorers"]), 3)
        self.assertEqual(context["top_scorers"][0]["player_name"], "Striker B")
        self.assertEqual(context["top_scorers"][0]["goals"], 8)
        self.assertEqual(context["top_scorers"][1]["player_name"], "Striker A")
        self.assertEqual(context["top_scorers"][2]["team_name"], "Gamma FC")

    def test_build_statistics_context_uses_player_photo_when_available(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            player = Player.objects.create(team=self.team_a, name="Striker Photo", number=9, position="FW", goals_scored=5)
            player.photo.save(
                "striker-photo.jpg",
                SimpleUploadedFile("striker-photo.jpg", b"photo-bytes", content_type="image/jpeg"),
                save=True,
            )

            context = build_statistics_context(category="seniors")

        self.assertEqual(context["top_scorers"][0]["player_name"], "Striker Photo")
        self.assertIn("striker-photo.jpg", context["top_scorers"][0]["player_photo"])

    def test_build_statistics_context_falls_back_when_player_photo_missing(self):
        Player.objects.create(team=self.team_a, name="Striker No Photo", number=9, position="FW", goals_scored=5)

        context = build_statistics_context(category="seniors")

        self.assertEqual(context["top_scorers"][0]["player_photo"], "/static/tournament/img/default_logo.jpg")

    def test_build_statistics_context_counts_cards_from_events(self):
        home_player = Player.objects.create(team=self.team_a, name="Midfielder A", number=8, position="MF")
        away_player = Player.objects.create(team=self.team_b, name="Defender B", number=5, position="DF")
        MatchEvent.objects.create(
            match=self.finished_match,
            player=home_player,
            team=self.team_a,
            event_type=MatchEvent.YELLOW_CARD,
            minute=18,
        )
        MatchEvent.objects.create(
            match=self.finished_match,
            player=away_player,
            team=self.team_b,
            event_type=MatchEvent.RED_CARD,
            minute=77,
        )

        context = build_statistics_context(category="seniors")

        self.assertEqual(context["total_yellow_cards"], 1)
        self.assertEqual(context["total_red_cards"], 1)
