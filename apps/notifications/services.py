from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import Notification, NotificationAudienceType, UserNotification

User = get_user_model()


def resolve_recipient_users(notification):
    recipients = set()

    if notification.audience_type == NotificationAudienceType.ALL:
        recipients.update(User.objects.filter(is_active=True).values_list("id", flat=True))

    elif notification.audience_type == NotificationAudienceType.ROLE:
        if notification.role:
            recipients.update(
                User.objects.filter(is_active=True, role=notification.role).values_list("id", flat=True)
            )

    elif notification.audience_type == NotificationAudienceType.USER:
        recipients.update(notification.target_users.filter(is_active=True).values_list("id", flat=True))

    elif notification.audience_type == NotificationAudienceType.TEAM:
        manager_ids = (
            notification.target_teams.filter(manager__isnull=False)
            .values_list("manager_id", flat=True)
            .distinct()
        )
        recipients.update(manager_ids)

    return recipients


@transaction.atomic
def dispatch_notification(notification):
    if not notification.is_active:
        return 0

    if notification.expires_at and notification.expires_at <= timezone.now():
        return 0

    recipient_ids = resolve_recipient_users(notification)
    created = 0

    for user_id in recipient_ids:
        _, was_created = UserNotification.objects.get_or_create(
            user_id=user_id,
            notification=notification,
        )
        if was_created:
            created += 1

    return created


@transaction.atomic
def create_and_dispatch_notification(*, title, message, category, audience_type, created_by=None, role="", target_users=None, target_teams=None, expires_at=None):
    notification = Notification.objects.create(
        title=title,
        message=message,
        category=category,
        audience_type=audience_type,
        created_by=created_by,
        role=role or "",
        expires_at=expires_at,
    )

    if target_users:
        notification.target_users.set(target_users)

    if target_teams:
        notification.target_teams.set(target_teams)

    dispatch_notification(notification)
    return notification
