from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import AppConfiguration, TEAM_MANAGER_ENABLE_PLAYERS
from apps.teams.models import Player, Team


class TeamCrudPermissionsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organizer = User.objects.create_user(
            username="organizer_test",
            password="Admin123*",
            role="ORGANIZER",
        )
        self.player = User.objects.create_user(
            username="player_test",
            password="Admin123*",
            role="PLAYER",
        )
        self.team_manager = User.objects.create_user(
            username="team_manager_test",
            password="Admin123*",
            role="TEAM_MANAGER",
        )
        self.team = Team.objects.create(
            name="Alpha Team",
            coach="Coach A",
            category="seniors",
        )

    def test_organizer_can_create_team(self):
        self.client.force_login(self.organizer)
        response = self.client.post(
            f"{reverse('team_create')}?category=seniors",
            {"name": "Beta Team", "coach": "Coach B"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Team.objects.filter(name="Beta Team", category="seniors").exists())

    def test_non_organizer_cannot_create_team(self):
        self.client.force_login(self.player)
        response = self.client.post(
            f"{reverse('team_create')}?category=seniors",
            {"name": "Gamma Team", "coach": "Coach G"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Team.objects.filter(name="Gamma Team").exists())

    def test_organizer_can_edit_team(self):
        self.client.force_login(self.organizer)
        response = self.client.post(
            f"{reverse('team_edit', kwargs={'team_id': self.team.id})}?category=seniors",
            {"name": "Alpha Updated", "coach": "Coach Z"},
        )

        self.assertEqual(response.status_code, 302)
        self.team.refresh_from_db()
        self.assertEqual(self.team.name, "Alpha Updated")

    def test_non_organizer_cannot_delete_team(self):
        self.client.force_login(self.player)
        response = self.client.post(
            f"{reverse('team_delete', kwargs={'team_id': self.team.id})}?category=seniors"
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Team.objects.filter(pk=self.team.id).exists())

    def test_organizer_can_create_player(self):
        self.client.force_login(self.organizer)
        response = self.client.post(
            f"{reverse('player_create', kwargs={'team_id': self.team.id})}?category=seniors",
            {"name": "Carlos", "number": 9, "position": "FW"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Player.objects.filter(team=self.team, name="Carlos").exists())

    def test_team_manager_cannot_create_player_when_setting_disabled(self):
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_create', kwargs={'team_id': self.team.id})}?category=seniors",
            {"name": "Pedro", "number": 10, "position": "MF"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Player.objects.filter(team=self.team, name="Pedro").exists())

    def test_team_manager_can_create_player_when_setting_enabled(self):
        AppConfiguration.objects.update_or_create(
            key=TEAM_MANAGER_ENABLE_PLAYERS,
            defaults={"is_enabled": True},
        )
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_create', kwargs={'team_id': self.team.id})}?category=seniors",
            {"name": "Mario", "number": 7, "position": "DF"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Player.objects.filter(team=self.team, name="Mario").exists())
