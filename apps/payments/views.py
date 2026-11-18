"""Views for card payment tracking."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.core.categories import get_request_championship_category
from apps.matches.models import MatchEvent
from apps.payments.forms import CardPaymentForm
from apps.payments.models import CardPayment
from apps.users.permissions import can_manage_match


@login_required
def card_payments_list(request):
    """Card payments list with filter: pendientes / pagados / todos."""
    category = get_request_championship_category(request)
    filtro = request.GET.get("filtro", "pendientes")
    if filtro not in ("pendientes", "pagados", "todos"):
        filtro = "pendientes"

    if getattr(request.user, "role", None) not in {"ORGANIZER", "ADMIN"} and not request.user.is_superuser:
        return HttpResponseForbidden("No tienes permisos para consultar estos pagos.")

    card_events = (
        MatchEvent.objects.filter(
            event_type__in=[MatchEvent.YELLOW_CARD, MatchEvent.RED_CARD],
            team__category=category,
        )
        .select_related("player", "team", "match", "match__match_day__tournament")
        .prefetch_related("card_payment")
        .order_by("team__name", "match__date", "minute")
    )
    if getattr(request.user, "role", None) == "ORGANIZER" and not request.user.is_superuser:
        card_events = card_events.filter(
            Q(match__match_day__tournament__isnull=True)
            | Q(match__match_day__tournament__organizers=request.user)
        )

    if filtro == "pendientes":
        pending_ids = []
        for event in card_events:
            try:
                if not event.card_payment.paid:
                    pending_ids.append(event.pk)
            except CardPayment.DoesNotExist:
                pending_ids.append(event.pk)
        card_events = card_events.filter(pk__in=pending_ids)
    elif filtro == "pagados":
        card_events = card_events.filter(card_payment__paid=True)

    for event in card_events:
        event.can_manage_payment = can_manage_match(request.user, event.match)

    return render(
        request,
        "payments/card_payments.html",
        {
            "card_events": card_events,
            "filtro": filtro,
        },
    )


@login_required
def register_card_payment(request, event_id):
    """Create or update the CardPayment record for a MatchEvent card."""
    category = get_request_championship_category(request)
    event = get_object_or_404(
        MatchEvent.objects.select_related("match__match_day__tournament"),
        pk=event_id,
        event_type__in=[MatchEvent.YELLOW_CARD, MatchEvent.RED_CARD],
        team__category=category,
    )
    can_edit_payment = can_manage_match(request.user, event.match)
    if not can_edit_payment:
        return HttpResponseForbidden("No tienes permisos para administrar este pago.")
    payment = CardPayment.objects.filter(match_event=event).first()

    if request.method == "POST":
        form = CardPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.match_event = event
            payment.save()
            return redirect(f"{reverse('card_payments')}?category={category}")
    else:
        form = CardPaymentForm(instance=payment)

    return render(
        request,
        "payments/register_payment.html",
        {"form": form, "event": event, "payment": payment, "can_edit_payment": can_edit_payment},
    )
