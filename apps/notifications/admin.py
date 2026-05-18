from django.contrib import admin

from apps.notifications.models import Notification, UserNotification
from apps.notifications.services import dispatch_notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "audience_type", "is_active", "created_at")
    list_filter = ("category", "audience_type", "is_active")
    search_fields = ("title", "message")
    filter_horizontal = ("target_users", "target_teams")
    actions = ["dispatch_selected"]

    @admin.action(description="Redistribuir notificaciones seleccionadas")
    def dispatch_selected(self, request, queryset):
        total = 0
        for notification in queryset:
            total += dispatch_notification(notification)
        self.message_user(request, f"Se generaron {total} entregas de notificacion.")


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "notification", "is_read", "delivered_at", "read_at")
    list_filter = ("is_read", "notification__category")
    search_fields = ("user__username", "notification__title")
