from django.contrib import admin

from apps.notifications.models import Notification, UserNotification, WebPushSubscription
from apps.notifications.services import dispatch_notification, send_push_for_notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "audience_type", "is_active", "created_at")
    list_filter = ("category", "audience_type", "is_active")
    search_fields = ("title", "message")
    filter_horizontal = ("target_users", "target_teams")
    actions = ["dispatch_selected", "send_push_selected"]

    @admin.action(description="Redistribuir notificaciones seleccionadas")
    def dispatch_selected(self, request, queryset):
        total = 0
        for notification in queryset:
            total += dispatch_notification(notification)
        self.message_user(request, f"Se generaron {total} entregas de notificacion.")

    @admin.action(description="Enviar push de notificaciones seleccionadas")
    def send_push_selected(self, request, queryset):
        sent = 0
        failed = 0
        deactivated = 0

        for notification in queryset:
            result = send_push_for_notification(notification)
            sent += result["sent"]
            failed += result["failed"]
            deactivated += result["deactivated"]

        self.message_user(
            request,
            f"Push enviados: {sent}. Fallidos: {failed}. Suscripciones desactivadas: {deactivated}.",
        )


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "notification", "is_read", "delivered_at", "read_at")
    list_filter = ("is_read", "notification__category")
    search_fields = ("user__username", "notification__title")


@admin.register(WebPushSubscription)
class WebPushSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "is_active",
        "last_success_at",
        "last_failure_at",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("user__username", "endpoint")
    readonly_fields = ("created_at", "updated_at", "last_success_at", "last_failure_at")
