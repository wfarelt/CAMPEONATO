from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.matches.models import Match
from apps.playoffs.models import LeagueSettings, PlayoffTie
from apps.playoffs.services import generate_playoff, record_penalty_result, resolve_tie
from apps.teams.models import Team
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
        self.assertTrue(playoff.ties.filter(round=PlayoffTie.FINAL).exists())
        self.assertTrue(playoff.ties.filter(round=PlayoffTie.THIRD_PLACE).exists())

    def test_home_and_away_creates_two_legs_with_best_seed_at_home_second(self):
        self.settings.playoffs_home_and_away = True
        self.settings.save(update_fields=["playoffs_home_and_away"])

        playoff = generate_playoff("seniors", date(2026, 6, 1), time(10, 0))

        tie = playoff.ties.get(round=PlayoffTie.QUARTERFINAL, position=1)
        self.assertEqual(tie.first_leg.home_team, self.teams[-1])
        self.assertEqual(tie.second_leg.home_team, self.teams[0])

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

    def test_settings_require_a_power_of_two(self):
        self.settings.teams_classified = 6
        with self.assertRaises(ValidationError):
            self.settings.full_clean()

    def test_playoffs_view_renders_the_active_bracket(self):
        generate_playoff("seniors", date(2026, 6, 1), time(10, 0))

        response = self.client.get(reverse("playoffs"), {"category": "seniors"})

        self.assertContains(response, "Cuadro eliminatorio")
        self.assertContains(response, "Cuartos de final")

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