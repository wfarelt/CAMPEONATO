from django.urls import path

from apps.notifications.views import (
    mark_notification_read,
    notification_create,
    notification_inbox,
    push_subscribe,
    push_unsubscribe,
    push_demo_from_view,
    service_worker,
)

urlpatterns = [
    path("notifications/", notification_inbox, name="notifications_inbox"),
    path("notifications/create/", notification_create, name="notifications_create"),
    path("notifications/push/subscribe/", push_subscribe, name="notifications_push_subscribe"),
    path("notifications/push/unsubscribe/", push_unsubscribe, name="notifications_push_unsubscribe"),
    path("notifications/push/demo/", push_demo_from_view, name="notifications_push_demo"),
    path("service-worker.js", service_worker, name="service_worker"),
    path(
        "notifications/<int:user_notification_id>/read/",
        mark_notification_read,
        name="notification_mark_read",
    ),
]
