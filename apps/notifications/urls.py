from django.urls import path

from apps.notifications.views import (
    mark_notification_read,
    notification_create,
    notification_inbox,
)

urlpatterns = [
    path("notifications/", notification_inbox, name="notifications_inbox"),
    path("notifications/create/", notification_create, name="notifications_create"),
    path(
        "notifications/<int:user_notification_id>/read/",
        mark_notification_read,
        name="notification_mark_read",
    ),
]
