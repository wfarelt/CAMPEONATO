import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from pywebpush import WebPushException, webpush

from apps.notifications.models import (
    Notification,
    NotificationAudienceType,
    UserNotification,
    WebPushSubscription,
)

User = get_user_model()


def build_notification_push_payload(notification, *, url=""):
    destination_url = url or "/notifications/"
    return {
        "title": notification.title,
        "body": notification.message,
        "icon": getattr(settings, "WEBPUSH_DEFAULT_ICON", "/static/tournament/img/favicon.png"),
        "image": "",
        "url": destination_url,
        "tag": f"notification-{notification.id}",
    }


def _mark_subscription_failure(subscription, reason, *, deactivate=False):
    subscription.last_failure_at = timezone.now()
    subscription.failure_reason = reason[:255]
    if deactivate:
        subscription.is_active = False
    subscription.save(update_fields=["last_failure_at", "failure_reason", "is_active", "updated_at"])


def send_web_push_to_subscription(subscription, payload):
    if not settings.WEBPUSH_PRIVATE_KEY or not settings.WEBPUSH_SUBJECT:
        _mark_subscription_failure(subscription, "Missing WEBPUSH_PRIVATE_KEY or WEBPUSH_SUBJECT")
        return False

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                },
            },
            data=json.dumps(payload),
            vapid_private_key=settings.WEBPUSH_PRIVATE_KEY,
            vapid_claims={"sub": settings.WEBPUSH_SUBJECT},
        )
    except WebPushException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        failure_reason = f"{exc}"
        should_deactivate = status_code in {404, 410}
        _mark_subscription_failure(subscription, failure_reason, deactivate=should_deactivate)
        return False

    subscription.last_success_at = timezone.now()
    subscription.failure_reason = ""
    subscription.save(update_fields=["last_success_at", "failure_reason", "updated_at"])
    return True


def send_web_push_to_user_ids(user_ids, payload):
    if not user_ids:
        return {"sent": 0, "failed": 0, "deactivated": 0}

    subscriptions = WebPushSubscription.objects.filter(
        user_id__in=user_ids,
        is_active=True,
    )

    sent = 0
    failed = 0
    deactivated = 0

    for subscription in subscriptions:
        was_active = subscription.is_active
        ok = send_web_push_to_subscription(subscription, payload)
        if ok:
            sent += 1
            continue

        failed += 1
        if was_active and not subscription.is_active:
            deactivated += 1

    return {"sent": sent, "failed": failed, "deactivated": deactivated}


def send_push_for_notification(notification, *, user_ids=None, url=""):
    recipient_ids = user_ids or resolve_recipient_users(notification)
    payload = build_notification_push_payload(notification, url=url)
    return send_web_push_to_user_ids(recipient_ids, payload)


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
def dispatch_notification(notification, *, send_push=False, push_url=""):
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

    if send_push and recipient_ids:
        send_push_for_notification(notification, user_ids=recipient_ids, url=push_url)

    return created


@transaction.atomic
def create_and_dispatch_notification(*, title, message, category, audience_type, created_by=None, role="", target_users=None, target_teams=None, expires_at=None, send_push=True, push_url=""):
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

    dispatch_notification(notification, send_push=send_push, push_url=push_url)
    return notification
