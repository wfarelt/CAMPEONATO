import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from pywebpush import WebPushException, webpush
import logging

logger = logging.getLogger(__name__)

from apps.notifications.models import (
    Notification,
    NotificationAudienceType,
    UserNotification,
    WebPushSubscription,
)

from apps.core.models import AppConfiguration, ENABLE_PUSH_NOTIFICATIONS

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
        logger.debug("Sending webpush to subscription %s for user %s", subscription.endpoint, subscription.user_id)
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
        logger.warning(
            "WebPushException for subscription %s user %s: %s (status=%s). Deactivate=%s",
            subscription.endpoint,
            subscription.user_id,
            failure_reason,
            status_code,
            should_deactivate,
        )
        _mark_subscription_failure(subscription, failure_reason, deactivate=should_deactivate)
        return False
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.exception("Unexpected error sending webpush to %s user %s: %s", subscription.endpoint, subscription.user_id, exc)
        _mark_subscription_failure(subscription, str(exc), deactivate=False)
        return False

    subscription.last_success_at = timezone.now()
    subscription.failure_reason = ""
    subscription.save(update_fields=["last_success_at", "failure_reason", "updated_at"])
    logger.debug("Webpush sent successfully to %s user %s", subscription.endpoint, subscription.user_id)
    return True


def send_web_push_to_user_ids(user_ids, payload):
    if not user_ids:
        return {"sent": 0, "failed": 0, "deactivated": 0}

    subscriptions = WebPushSubscription.objects.filter(
        user_id__in=user_ids,
        is_active=True,
    )

    if not subscriptions.exists():
        logger.warning("No active web push subscriptions for user_ids=%s", list(user_ids))

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

    logger.warning("Webpush summary for payload tag=%s: sent=%s failed=%s deactivated=%s", payload.get("tag"), sent, failed, deactivated)
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
        try:
            push_config = AppConfiguration.objects.filter(key=ENABLE_PUSH_NOTIFICATIONS).first()
            if push_config is not None and not push_config.is_enabled:
                logger.info("Push notifications disabled by AppConfiguration; skipping push dispatch")
            else:
                send_push_for_notification(notification, user_ids=recipient_ids, url=push_url)
        except Exception:
            # If config can't be read for any reason, proceed with sending push to avoid
            # silently dropping notifications. Log the exception for diagnosis.
            logger.exception("Error reading push configuration; proceeding to send push notifications")
            send_push_for_notification(notification, user_ids=recipient_ids, url=push_url)

    return created


@transaction.atomic
def create_and_dispatch_notification(*, title, message, category, audience_type, created_by=None, role="", target_users=None, target_teams=None, expires_at=None, send_push=True, push_url=""):
    # If global push notifications are disabled, do not create any Notification
    # records (user requested behaviour). Check config before creating.
    try:
        push_config = AppConfiguration.objects.filter(key=ENABLE_PUSH_NOTIFICATIONS).first()
        if push_config is not None and not push_config.is_enabled:
            logger.info("Global push notifications disabled via AppConfiguration; skipping creation of notification for title=%s", title)
            return None
    except Exception:
        logger.exception("Error reading AppConfiguration for push notifications; proceeding to create notification")

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

    # Respect global app configuration for push notifications. If the setting
    # exists and is disabled, force send_push to False to avoid sending webpush.
    try:
        push_config = AppConfiguration.objects.filter(key=ENABLE_PUSH_NOTIFICATIONS).first()
        if push_config is not None and not push_config.is_enabled:
            logger.info("Global push notifications disabled via AppConfiguration; not sending push for notification %s", notification.pk)
            send_push = False
    except Exception:
        logger.exception("Error reading AppConfiguration for push notifications; proceeding with original send_push=%s", send_push)

    dispatch_notification(notification, send_push=send_push, push_url=push_url)
    return notification
