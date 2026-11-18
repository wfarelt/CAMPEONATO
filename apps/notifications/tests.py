from django.test import TestCase
from django.urls import reverse

from apps.notifications.models import Notification, NotificationAudienceType, NotificationCategory
from apps.notifications.services import resolve_recipient_users
from apps.teams.models import Team
from apps.users.models import User


class GlobalNotificationPermissionTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="notification-organizer", password="secret", role="ORGANIZER")
        self.admin = User.objects.create_user(username="notification-admin", password="secret", role="ADMIN")

    def test_organizer_cannot_send_global_notification(self):
        self.client.force_login(self.organizer)

        response = self.client.post(
            reverse("notifications_create"),
            {
                "title": "Aviso global",
                "message": "Mensaje",
                "category": NotificationCategory.SYSTEM,
                "audience_type": NotificationAudienceType.ALL,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Notification.objects.exists())

    def test_platform_admin_can_send_global_notification(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("notifications_create"),
            {
                "title": "Aviso global",
                "message": "Mensaje",
                "category": NotificationCategory.SYSTEM,
                "audience_type": NotificationAudienceType.ALL,
            },
        )

        self.assertRedirects(response, reverse("notifications_inbox"), fetch_redirect_response=False)
        self.assertTrue(Notification.objects.filter(title="Aviso global", audience_type="ALL").exists())

    def test_team_notification_only_targets_managers_of_selected_teams(self):
        manager = User.objects.create_user(username="team-manager", password="secret", role="TEAM_MANAGER")
        unrelated_manager = User.objects.create_user(
            username="unrelated-manager",
            password="secret",
            role="TEAM_MANAGER",
        )
        selected_team = Team.objects.create(
            name="Selected Team",
            coach="Coach",
            category="seniors",
            manager=manager,
        )
        Team.objects.create(
            name="Unrelated Team",
            coach="Coach",
            category="seniors",
            manager=unrelated_manager,
        )
        notification = Notification.objects.create(
            title="Fixture",
            message="Hay una jornada nueva",
            category=NotificationCategory.MATCH,
            audience_type=NotificationAudienceType.TEAM,
        )
        notification.target_teams.add(selected_team)

        self.assertEqual(resolve_recipient_users(notification), {manager.pk})
