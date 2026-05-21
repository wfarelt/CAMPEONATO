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
            manager=self.team_manager,
        )
        self.other_team = Team.objects.create(
            name="Omega Team",
            coach="Coach O",
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

    def test_organizer_can_create_reinforcement_player(self):
        self.client.force_login(self.organizer)
        response = self.client.post(
            f"{reverse('player_create', kwargs={'team_id': self.team.id})}?category=seniors",
            {"name": "Carlos Refuerzo", "number": 19, "position": "FW", "is_reinforcement": "on"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Player.objects.filter(team=self.team, name="Carlos Refuerzo", is_reinforcement=True).exists()
        )

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

    def test_team_manager_cannot_create_player_for_other_team(self):
        AppConfiguration.objects.update_or_create(
            key=TEAM_MANAGER_ENABLE_PLAYERS,
            defaults={"is_enabled": True},
        )
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_create', kwargs={'team_id': self.other_team.id})}?category=seniors",
            {"name": "Rival", "number": 8, "position": "MF"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Player.objects.filter(team=self.other_team, name="Rival").exists())

    def test_team_manager_cannot_edit_player(self):
        player = Player.objects.create(team=self.team, name="Mario", number=7, position="DF")
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_edit', kwargs={'team_id': self.team.id, 'player_id': player.id})}?category=seniors",
            {"name": "Mario Editado", "number": 7, "position": "DF"},
        )

        self.assertEqual(response.status_code, 403)
        player.refresh_from_db()
        self.assertEqual(player.name, "Mario")

    def test_team_manager_can_edit_player_when_setting_enabled(self):
        AppConfiguration.objects.update_or_create(
            key=TEAM_MANAGER_ENABLE_PLAYERS,
            defaults={"is_enabled": True},
        )
        player = Player.objects.create(team=self.team, name="Mario", number=7, position="DF")
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_edit', kwargs={'team_id': self.team.id, 'player_id': player.id})}?category=seniors",
            {"name": "Mario Editado", "number": 7, "position": "DF"},
        )

        self.assertEqual(response.status_code, 302)
        player.refresh_from_db()
        self.assertEqual(player.name, "Mario Editado")

    def test_team_manager_cannot_delete_player_from_other_team(self):
        AppConfiguration.objects.update_or_create(
            key=TEAM_MANAGER_ENABLE_PLAYERS,
            defaults={"is_enabled": True},
        )
        player = Player.objects.create(team=self.other_team, name="Rival", number=8, position="MF")
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_delete', kwargs={'team_id': self.other_team.id, 'player_id': player.id})}?category=seniors"
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Player.objects.filter(pk=player.id).exists())

    def test_team_manager_can_delete_player_from_assigned_team(self):
        AppConfiguration.objects.update_or_create(
            key=TEAM_MANAGER_ENABLE_PLAYERS,
            defaults={"is_enabled": True},
        )
        player = Player.objects.create(team=self.team, name="Mario", number=7, position="DF")
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_delete', kwargs={'team_id': self.team.id, 'player_id': player.id})}?category=seniors"
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Player.objects.filter(pk=player.id).exists())

    def test_team_players_are_ordered_by_position(self):
        self.client.force_login(self.organizer)
        Player.objects.create(team=self.team, name="Delantero", number=9, position="FW")
        Player.objects.create(team=self.team, name="Arquero", number=1, position="GK")
        Player.objects.create(team=self.team, name="Defensa", number=4, position="DF")
        Player.objects.create(team=self.team, name="Mediocampo", number=6, position="MF")

        response = self.client.get(f"{reverse('team', kwargs={'team_id': self.team.id})}?category=seniors")

        self.assertEqual(response.status_code, 200)
        positions = [player.position for player in response.context["team_players"]]
        self.assertEqual(positions, ["GK", "DF", "MF", "FW"])

    def test_team_default_is_available_for_matchday(self):
        self.assertTrue(self.team.is_available_for_matchday)

    def test_organizer_can_toggle_team_availability(self):
        self.client.force_login(self.organizer)
        response = self.client.post(
            f"{reverse('team_edit', kwargs={'team_id': self.team.id})}?category=seniors",
            {
                "name": self.team.name,
                "coach": self.team.coach,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.team.refresh_from_db()
        self.assertFalse(self.team.is_available_for_matchday)
