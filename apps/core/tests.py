from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import TEAM_MANAGER_ENABLE_PLAYERS, AppConfiguration


class CoreSettingsViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.organizer = user_model.objects.create_user(
            username="organizer_settings",
            password="Admin123*",
            role="ORGANIZER",
        )
        self.team_manager = user_model.objects.create_user(
            username="tm_settings",
            password="Admin123*",
            role="TEAM_MANAGER",
        )

    def test_only_organizer_can_access_settings_view(self):
        self.client.force_login(self.team_manager)
        response = self.client.get(f"{reverse('settings')}?category=seniors")
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.organizer)
        response = self.client.get(f"{reverse('settings')}?category=seniors")
        self.assertEqual(response.status_code, 200)

    def test_organizer_can_toggle_first_setting(self):
        self.client.force_login(self.organizer)
        self.client.get(f"{reverse('settings')}?category=seniors")

        response = self.client.post(
            f"{reverse('settings')}?category=seniors",
            {"key": TEAM_MANAGER_ENABLE_PLAYERS, "is_enabled": "on"},
        )

        self.assertEqual(response.status_code, 302)
        config = AppConfiguration.objects.get(key=TEAM_MANAGER_ENABLE_PLAYERS)
        self.assertTrue(config.is_enabled)
