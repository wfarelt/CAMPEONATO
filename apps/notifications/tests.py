from django.test import TestCase
from django.urls import reverse

from apps.notifications.models import (
    Notification,
    NotificationAudienceType,
    NotificationCategory,
    UserNotification,
)
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

    def test_platform_admin_sees_bootstrap_notification_form(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("notifications_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="row g-3"')
        self.assertContains(response, 'class="form-select"')
        self.assertContains(response, 'class="btn btn-primary"')

    def test_inbox_renders_unread_notification_with_bootstrap_controls(self):
        notification = Notification.objects.create(
            title="Aviso de prueba",
            message="La jornada comienza pronto.",
            category=NotificationCategory.MATCH,
            audience_type=NotificationAudienceType.ALL,
        )
        UserNotification.objects.create(user=self.organizer, notification=notification)
        self.client.force_login(self.organizer)

        response = self.client.get(reverse("notifications_inbox"), {"filter": "unread"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Filtrar notificaciones"')
        self.assertContains(response, 'class="nav-link active"')
        self.assertContains(response, 'id="enable-push-btn"')
        self.assertContains(response, "Aviso de prueba")
        self.assertContains(response, "Marcar leida")
        self.assertContains(response, "push-subscription.js")

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
