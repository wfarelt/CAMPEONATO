from django.utils import timezone

from apps.notifications.models import UserNotification


def notifications_context(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"unread_notifications_count": 0}

    unread_count = UserNotification.objects.filter(
        user=request.user,
        is_read=False,
        notification__is_active=True,
    ).exclude(notification__expires_at__lte=timezone.now()).count()
    return {"unread_notifications_count": unread_count}
