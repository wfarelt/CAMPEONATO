from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.choices import USER_ROLE_CHOICES


class NotificationCategory(models.TextChoices):
    SYSTEM = "SYSTEM", "Sistema"
    MATCH = "MATCH", "Partidos"
    TEAM = "TEAM", "Equipos"
    STANDINGS = "STANDINGS", "Clasificaciones"
    PAYMENT = "PAYMENT", "Pagos"
    REMINDER = "REMINDER", "Recordatorios"


class NotificationAudienceType(models.TextChoices):
    ALL = "ALL", "Todos"
    TEAM = "TEAM", "Por equipo"
    USER = "USER", "Por usuario"
    ROLE = "ROLE", "Por rol"


class Notification(models.Model):
    title = models.CharField(max_length=140)
    message = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=NotificationCategory.choices,
        default=NotificationCategory.SYSTEM,
    )
    audience_type = models.CharField(
        max_length=10,
        choices=NotificationAudienceType.choices,
        default=NotificationAudienceType.ALL,
    )
    role = models.CharField(max_length=20, choices=USER_ROLE_CHOICES, blank=True)
    target_teams = models.ManyToManyField("teams.Team", blank=True, related_name="notifications")
    target_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="target_notifications")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notifications",
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.category}] {self.title}"

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())


class UserNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="deliveries")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-delivered_at"]
        unique_together = ("user", "notification")

    def __str__(self):
        return f"{self.user} -> {self.notification}"


class WebPushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="web_push_subscriptions",
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    expiration_time = models.DateTimeField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        endpoint_preview = self.endpoint[:80]
        return f"{self.user} -> {endpoint_preview}"
