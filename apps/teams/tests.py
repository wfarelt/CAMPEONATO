from django.contrib.auth import get_user_model
from datetime import date, time
from django.test import TestCase
from django.urls import reverse

from apps.core.models import (
    AppConfiguration,
    TEAM_MANAGER_ENABLE_PLAYERS,
    TEAM_MANAGER_EDIT_TEAM,
    PLAYER_FIELD_BIRTH_DATE,
    PLAYER_FIELD_GRADUATION_YEAR,
    PLAYER_FIELD_PHOTO,
    PLAYER_FIELD_SUB35,
)
from apps.teams.forms import PlayerForm
from apps.matches.models import Match, MatchEvent
from apps.payments.models import CardPayment
from apps.teams.models import Player, Team
from apps.tournaments.models import MatchDay, Tournament, TournamentPlayer, TournamentTeam


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

    def test_team_form_renders_bootstrap_fields(self):
        self.client.force_login(self.organizer)

        response = self.client.get(f"{reverse('team_create')}?category=seniors")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "class=\"row g-3\"")
        self.assertContains(response, "form-control")
        self.assertContains(response, "Disponible para jornada")

    def test_team_list_renders_bootstrap_grid_and_team_data(self):
        self.client.force_login(self.organizer)

        response = self.client.get(f"{reverse('teams')}?category=seniors")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/static/tournament/css/teams.css"')
        self.assertContains(response, 'src="/static/teams/js/teams.js"')
        self.assertContains(response, 'class="app-body app-body--teams"')
        self.assertContains(response, "row row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xxl-4 g-3")
        self.assertContains(response, "app-team-card")
        self.assertContains(response, self.team.name)

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
            f"{reverse('team_edit', kwargs={'team_slug': self.team.slug})}?category=seniors",
            {"name": "Alpha Updated", "coach": "Coach Z"},
        )

        self.assertEqual(response.status_code, 302)
        self.team.refresh_from_db()
        self.assertEqual(self.team.name, "Alpha Updated")

    def test_non_organizer_cannot_delete_team(self):
        self.client.force_login(self.player)
        response = self.client.post(
            f"{reverse('team_delete', kwargs={'team_slug': self.team.slug})}?category=seniors"
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Team.objects.filter(pk=self.team.id).exists())

    def test_team_delete_confirmation_uses_bootstrap(self):
        self.client.force_login(self.organizer)

        response = self.client.get(
            f"{reverse('team_delete', kwargs={'team_slug': self.team.slug})}?category=seniors"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "app-surface border border-danger rounded-3")
        self.assertContains(response, "btn btn-danger")

    def test_team_manager_can_edit_team_profile_with_permission_enabled(self):
        AppConfiguration.objects.update_or_create(
            key=TEAM_MANAGER_EDIT_TEAM,
            defaults={"is_enabled": True},
        )
        self.client.force_login(self.team_manager)

        response = self.client.get(
            f"{reverse('team_manager_settings', kwargs={'team_slug': self.team.slug})}?category=seniors"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "class=\"app-surface border rounded-3 p-3 p-md-4\"")
        update_response = self.client.post(
            f"{reverse('team_manager_settings', kwargs={'team_slug': self.team.slug})}?category=seniors",
            {"coach": "New Coach"},
        )

        self.assertEqual(update_response.status_code, 302)
        self.team.refresh_from_db()
        self.assertEqual(self.team.coach, "New Coach")

    def test_organizer_can_create_player(self):
        self.client.force_login(self.organizer)
        response = self.client.post(
            f"{reverse('player_create', kwargs={'team_slug': self.team.slug})}?category=seniors",
            {"name": "Carlos", "number": 9, "position": "FW"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Player.objects.filter(team=self.team, name="Carlos").exists())

    def test_organizer_can_create_reinforcement_player(self):
        self.client.force_login(self.organizer)
        response = self.client.post(
            f"{reverse('player_create', kwargs={'team_slug': self.team.slug})}?category=seniors",
            {"name": "Carlos Refuerzo", "number": 19, "position": "FW", "is_reinforcement": "on"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Player.objects.filter(team=self.team, name="Carlos Refuerzo", is_reinforcement=True).exists()
        )

    def test_team_manager_cannot_create_player_when_setting_disabled(self):
        AppConfiguration.objects.update_or_create(
            key=TEAM_MANAGER_ENABLE_PLAYERS,
            defaults={"is_enabled": False},
        )
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_create', kwargs={'team_slug': self.team.slug})}?category=seniors",
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
            f"{reverse('player_create', kwargs={'team_slug': self.team.slug})}?category=seniors",
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
            f"{reverse('player_create', kwargs={'team_slug': self.other_team.slug})}?category=seniors",
            {"name": "Rival", "number": 8, "position": "MF"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Player.objects.filter(team=self.other_team, name="Rival").exists())

    def test_player_delete_confirmation_uses_bootstrap(self):
        player = Player.objects.create(team=self.team, name="Mario", number=7, position="DF")
        self.client.force_login(self.organizer)

        response = self.client.get(
            f"{reverse('player_delete', kwargs={'team_slug': self.team.slug, 'player_id': player.id})}?category=seniors"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "app-surface border border-danger rounded-3")
        self.assertContains(response, "btn btn-danger")

    def test_team_manager_cannot_edit_player(self):
        AppConfiguration.objects.update_or_create(
            key=TEAM_MANAGER_ENABLE_PLAYERS,
            defaults={"is_enabled": False},
        )
        player = Player.objects.create(team=self.team, name="Mario", number=7, position="DF")
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_edit', kwargs={'team_slug': self.team.slug, 'player_id': player.id})}?category=seniors",
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
            f"{reverse('player_edit', kwargs={'team_slug': self.team.slug, 'player_id': player.id})}?category=seniors",
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
            f"{reverse('player_delete', kwargs={'team_slug': self.other_team.slug, 'player_id': player.id})}?category=seniors"
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
            f"{reverse('player_delete', kwargs={'team_slug': self.team.slug, 'player_id': player.id})}?category=seniors"
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Player.objects.filter(pk=player.id).exists())

    def test_team_manager_can_edit_and_delete_assigned_player_by_default(self):
        player = Player.objects.create(team=self.team, name="Mario", number=7, position="DF")
        self.client.force_login(self.team_manager)

        edit_response = self.client.post(
            f"{reverse('player_edit', kwargs={'team_slug': self.team.slug, 'player_id': player.id})}?category=seniors",
            {"name": "Mario Editado", "number": 7, "position": "DF"},
        )

        self.assertEqual(edit_response.status_code, 302)
        player.refresh_from_db()
        self.assertEqual(player.name, "Mario Editado")

        delete_response = self.client.post(
            f"{reverse('player_delete', kwargs={'team_slug': self.team.slug, 'player_id': player.id})}?category=seniors"
        )

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Player.objects.filter(pk=player.id).exists())

    def test_team_players_are_ordered_by_position(self):
        self.client.force_login(self.organizer)
        Player.objects.create(team=self.team, name="Delantero", number=9, position="FW")
        Player.objects.create(team=self.team, name="Arquero", number=1, position="GK")
        Player.objects.create(team=self.team, name="Defensa", number=4, position="DF")
        Player.objects.create(team=self.team, name="Mediocampo", number=6, position="MF")

        response = self.client.get(f"{reverse('team', kwargs={'team_slug': self.team.slug})}?category=seniors")

        self.assertEqual(response.status_code, 200)
        positions = [player.position for player in response.context["team_players"]]
        self.assertEqual(positions, ["GK", "DF", "MF", "FW"])

    def test_team_detail_renders_bootstrap_sections_and_photo_modal(self):
        self.client.force_login(self.organizer)

        response = self.client.get(f"{reverse('team', kwargs={'team_slug': self.team.slug})}?category=seniors")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "class=\"row g-4\"")
        self.assertContains(response, "app-surface border rounded-3")
        self.assertContains(response, "id=\"playerPhotoModal\"")
        self.assertContains(response, 'src="/static/tournament/img/default_logo.jpg"')
        self.assertContains(response, "Sin jugadores registrados")

    def test_team_detail_includes_only_pending_card_payments(self):
        player = Player.objects.create(team=self.team, name="Mario", number=7, position="DF")
        match = Match.objects.create(
            home_team=self.team,
            away_team=self.other_team,
            date=date(2026, 6, 1),
            time="10:00",
        )
        pending_event = MatchEvent.objects.create(
            match=match,
            player=player,
            team=self.team,
            event_type=MatchEvent.YELLOW_CARD,
        )
        paid_event = MatchEvent.objects.create(
            match=match,
            player=player,
            team=self.team,
            event_type=MatchEvent.RED_CARD,
        )
        CardPayment.objects.create(match_event=paid_event, paid=True)
        self.client.force_login(self.organizer)

        response = self.client.get(f"{reverse('team', kwargs={'team_slug': self.team.slug})}?category=seniors")

        self.assertEqual(list(response.context["pending_card_events"]), [pending_event])

    def test_player_form_hides_extra_fields_when_disabled(self):
        AppConfiguration.objects.update_or_create(key=PLAYER_FIELD_GRADUATION_YEAR, defaults={"is_enabled": False})
        AppConfiguration.objects.update_or_create(key=PLAYER_FIELD_BIRTH_DATE, defaults={"is_enabled": False})
        AppConfiguration.objects.update_or_create(key=PLAYER_FIELD_PHOTO, defaults={"is_enabled": False})
        AppConfiguration.objects.update_or_create(key=PLAYER_FIELD_SUB35, defaults={"is_enabled": False})

        form = PlayerForm()

        self.assertNotIn("graduation_year", form.fields)
        self.assertNotIn("birth_date", form.fields)
        self.assertNotIn("photo", form.fields)
        self.assertNotIn("is_sub35", form.fields)

    def test_player_form_includes_extra_fields_when_enabled(self):
        AppConfiguration.objects.update_or_create(key=PLAYER_FIELD_GRADUATION_YEAR, defaults={"is_enabled": True})
        AppConfiguration.objects.update_or_create(key=PLAYER_FIELD_BIRTH_DATE, defaults={"is_enabled": True})
        AppConfiguration.objects.update_or_create(key=PLAYER_FIELD_PHOTO, defaults={"is_enabled": True})
        AppConfiguration.objects.update_or_create(key=PLAYER_FIELD_SUB35, defaults={"is_enabled": True})

        form = PlayerForm()

        self.assertIn("graduation_year", form.fields)
        self.assertIn("birth_date", form.fields)
        self.assertIn("photo", form.fields)
        self.assertIn("is_sub35", form.fields)

    def test_player_form_renders_saved_birth_date_for_editing(self):
        AppConfiguration.objects.update_or_create(
            key=PLAYER_FIELD_BIRTH_DATE,
            defaults={"is_enabled": True},
        )
        player = Player.objects.create(
            team=self.team,
            name="Carlos",
            number=10,
            position="MF",
            birth_date=date(1990, 5, 12),
        )

        form = PlayerForm(instance=player)

        self.assertIn('value="1990-05-12"', form["birth_date"].as_widget())

    def test_team_manager_cannot_edit_goals(self):
        AppConfiguration.objects.update_or_create(
            key=TEAM_MANAGER_ENABLE_PLAYERS,
            defaults={"is_enabled": True},
        )
        player = Player.objects.create(team=self.team, name="Mario", number=7, position="DF", goals_scored=3)
        self.client.force_login(self.team_manager)
        response = self.client.post(
            f"{reverse('player_edit', kwargs={'team_slug': self.team.slug, 'player_id': player.id})}?category=seniors",
            {"name": "Mario", "number": 7, "position": "DF", "goals_scored": 99},
        )

        self.assertEqual(response.status_code, 302)
        player.refresh_from_db()
        self.assertEqual(player.goals_scored, 3)

    def test_organizer_can_edit_goals(self):
        player = Player.objects.create(team=self.team, name="Mario", number=7, position="DF", goals_scored=3)
        self.client.force_login(self.organizer)
        response = self.client.post(
            f"{reverse('player_edit', kwargs={'team_slug': self.team.slug, 'player_id': player.id})}?category=seniors",
            {"name": "Mario", "number": 7, "position": "DF", "goals_scored": 15},
        )

        self.assertEqual(response.status_code, 302)
        player.refresh_from_db()
        self.assertEqual(player.goals_scored, 15)

    def test_team_default_is_available_for_matchday(self):
        self.assertTrue(self.team.is_available_for_matchday)

    def test_organizer_can_toggle_team_availability(self):
        self.client.force_login(self.organizer)
        response = self.client.post(
            f"{reverse('team_edit', kwargs={'team_slug': self.team.slug})}?category=seniors",
            {
                "name": self.team.name,
                "coach": self.team.coach,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.team.refresh_from_db()
        self.assertFalse(self.team.is_available_for_matchday)


class TournamentPlayerRosterViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organizer = User.objects.create_user(username="roster-organizer", password="secret", role="ORGANIZER")
        self.client.force_login(self.organizer)
        self.team = Team.objects.create(name="Roster Team", coach="Coach", category="seniors")
        self.opponent = Team.objects.create(name="Roster Opponent", coach="Coach", category="seniors")
        self.previous_tournament = Tournament.objects.create(name="Liga", season="2025", category="seniors")
        self.previous_tournament.organizers.add(self.organizer)
        self.previous_tournament.teams.add(self.team)
        self.tournament = Tournament.objects.create(name="Liga", season="2026", category="seniors")
        self.tournament.organizers.add(self.organizer)
        self.tournament.teams.add(self.team, self.opponent)

    def test_new_player_is_registered_only_in_selected_tournament(self):
        response = self.client.post(
            f"{reverse('player_create', kwargs={'team_slug': self.team.slug})}?category=seniors&tournament={self.tournament.pk}",
            {"name": "New Season Player", "number": 9, "position": "FW"},
        )

        self.assertEqual(response.status_code, 302)
        player = Player.objects.get(team=self.team, name="New Season Player")
        self.assertTrue(
            TournamentPlayer.objects.filter(
                tournament_team__tournament=self.tournament,
                player=player,
                is_active=True,
            ).exists()
        )
        self.assertFalse(
            TournamentPlayer.objects.filter(tournament_team__tournament=self.previous_tournament, player=player).exists()
        )

    def test_removing_and_reinscribing_player_preserves_match_history(self):
        player = Player.objects.create(team=self.team, name="Returning Player", position="FW")
        tournament_team = TournamentTeam.objects.get(tournament=self.tournament, team=self.team)
        roster_entry = TournamentPlayer.objects.create(tournament_team=tournament_team, player=player)
        matchday = MatchDay.objects.create(
            tournament=self.tournament,
            category="seniors",
            date=date(2026, 6, 1),
        )
        match = Match.objects.create(
            match_day=matchday,
            home_team=self.team,
            away_team=self.opponent,
            date=matchday.date,
            time=time(17, 0),
        )
        event = MatchEvent.objects.create(
            match=match,
            player=player,
            team=self.team,
            event_type=MatchEvent.GOAL,
        )
        query = f"category=seniors&tournament={self.tournament.pk}"

        response = self.client.post(
            f"{reverse('player_delete', kwargs={'team_slug': self.team.slug, 'player_id': player.pk})}?{query}"
        )

        self.assertEqual(response.status_code, 302)
        roster_entry.refresh_from_db()
        self.assertFalse(roster_entry.is_active)
        self.assertTrue(Player.objects.filter(pk=player.pk).exists())
        self.assertTrue(MatchEvent.objects.filter(pk=event.pk).exists())

        repeated_response = self.client.post(
            f"{reverse('player_delete', kwargs={'team_slug': self.team.slug, 'player_id': player.pk})}?{query}"
        )

        self.assertEqual(repeated_response.status_code, 302)
        self.assertTrue(Player.objects.filter(pk=player.pk).exists())
        self.assertTrue(MatchEvent.objects.filter(pk=event.pk).exists())

        response = self.client.post(
            f"{reverse('player_register', kwargs={'team_slug': self.team.slug})}?{query}",
            {"player": player.pk},
        )

        self.assertEqual(response.status_code, 302)
        roster_entry.refresh_from_db()
        self.assertTrue(roster_entry.is_active)
