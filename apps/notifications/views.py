import json
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.notifications.forms import NotificationCreateForm
from apps.notifications.models import UserNotification, WebPushSubscription
from apps.notifications.services import create_and_dispatch_notification, send_web_push_to_user_ids
from apps.users.permissions import organizer_required


@login_required
def notification_inbox(request):
    category = request.GET.get("filter", "all")

    queryset = UserNotification.objects.select_related("notification").filter(
        user=request.user,
        notification__is_active=True,
    )

    queryset = queryset.exclude(notification__expires_at__lte=timezone.now())

    if category == "unread":
        queryset = queryset.filter(is_read=False)
    elif category != "all":
        queryset = queryset.filter(notification__category=category)

    return render(
        request,
        "notifications/inbox.html",
        {
            "notifications": queryset,
            "active_filter": category,
            "web_push_public_key": settings.WEBPUSH_PUBLIC_KEY,
            "web_push_subscribe_url": "notifications_push_subscribe",
            "web_push_unsubscribe_url": "notifications_push_unsubscribe",
        },
    )


@login_required
def mark_notification_read(request, user_notification_id):
    if request.method != "POST":
        return redirect("notifications_inbox")

    user_notification = get_object_or_404(UserNotification, pk=user_notification_id, user=request.user)
    if not user_notification.is_read:
        user_notification.is_read = True
        user_notification.read_at = timezone.now()
        user_notification.save(update_fields=["is_read", "read_at"])

    return redirect(request.POST.get("next") or "notifications_inbox")


@login_required
@organizer_required
def notification_create(request):
    if request.method == "POST":
        form = NotificationCreateForm(request.POST)
        if form.is_valid():
            create_and_dispatch_notification(
                title=form.cleaned_data["title"],
                message=form.cleaned_data["message"],
                category=form.cleaned_data["category"],
                audience_type=form.cleaned_data["audience_type"],
                role=form.cleaned_data.get("role") or "",
                target_users=form.cleaned_data.get("target_users"),
                target_teams=form.cleaned_data.get("target_teams"),
                expires_at=form.cleaned_data.get("expires_at"),
                created_by=request.user,
            )
            messages.success(request, "Notificacion enviada correctamente.")
            return redirect("notifications_inbox")
    else:
        form = NotificationCreateForm()

    return render(request, "notifications/create.html", {"form": form})


@login_required
@require_POST
def push_subscribe(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        subscription = payload.get("subscription") or {}
        endpoint = subscription["endpoint"]
        keys = subscription["keys"]
        p256dh = keys["p256dh"]
        auth = keys["auth"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({"ok": False, "error": "Invalid subscription payload."}, status=400)

    expiration_time = subscription.get("expirationTime")
    expiration_datetime = None
    if expiration_time:
        expiration_datetime = datetime.fromtimestamp(expiration_time / 1000, tz=dt_timezone.utc)

    WebPushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh,
            "auth": auth,
            "expiration_time": expiration_datetime,
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            "is_active": True,
            "failure_reason": "",
        },
    )

    return JsonResponse({"ok": True, "status": "subscribed"})


@login_required
@require_POST
def push_unsubscribe(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid unsubscribe payload."}, status=400)

    endpoint = payload.get("endpoint", "")
    if not endpoint:
        return JsonResponse({"ok": False, "error": "Missing endpoint."}, status=400)

    WebPushSubscription.objects.filter(user=request.user, endpoint=endpoint).update(
        is_active=False,
        last_failure_at=timezone.now(),
        failure_reason="Unsubscribed by user",
    )
    return JsonResponse({"ok": True, "status": "unsubscribed"})


@require_GET
def service_worker(request):
    script = render(request, "notifications/service-worker.js").content
    response = HttpResponse(script, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


@login_required
@organizer_required
@require_POST
def push_demo_from_view(request):
    payload = {
        "title": "⚽ Partido Próximo",
        "body": "PROMO 2001T vs PROMO 98K inicia en 30 minutos",
        "icon": settings.WEBPUSH_DEFAULT_ICON,
        "url": "/match/15/",
        "vibrate": [100, 50, 100],
        "actions": [{"action": "open", "title": "Ver partido"}],
    }
    result = send_web_push_to_user_ids([request.user.id], payload)
    messages.info(
        request,
        f"Push demo -> enviados: {result['sent']}, fallidos: {result['failed']}, desactivadas: {result['deactivated']}",
    )
    return redirect("notifications_inbox")
