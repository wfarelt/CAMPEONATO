from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.notifications.forms import NotificationCreateForm
from apps.notifications.models import UserNotification
from apps.notifications.services import create_and_dispatch_notification
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
