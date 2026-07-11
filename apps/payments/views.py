"""Views for card payment tracking."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.categories import get_request_championship_category
from apps.matches.models import MatchEvent
from apps.payments.forms import CardPaymentForm
from apps.payments.models import CardPayment


@login_required
def card_payments_list(request):
    """Card payments list with filter: pendientes / pagados / todos."""
    category = get_request_championship_category(request)
    filtro = request.GET.get("filtro", "pendientes")
    if filtro not in ("pendientes", "pagados", "todos"):
        filtro = "pendientes"

    card_events = (
        MatchEvent.objects.filter(
            event_type__in=[MatchEvent.YELLOW_CARD, MatchEvent.RED_CARD],
            team__category=category,
        )
        .select_related("player", "team", "match", "match__match_day")
        .prefetch_related("card_payment")
        .order_by("team__name", "match__date", "minute")
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
        MatchEvent,
        pk=event_id,
        event_type__in=[MatchEvent.YELLOW_CARD, MatchEvent.RED_CARD],
        team__category=category,
    )
    payment, _ = CardPayment.objects.get_or_create(match_event=event)

    if request.method == "POST":
        form = CardPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            return redirect("card_payments")
    else:
        form = CardPaymentForm(instance=payment)

    return render(
        request,
        "payments/register_payment.html",
        {"form": form, "event": event, "payment": payment},
    )
