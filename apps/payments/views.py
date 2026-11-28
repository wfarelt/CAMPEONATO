"""Views for card payment tracking."""

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.db import OperationalError, connection, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from uuid import uuid4
import logging

from apps.core.categories import get_request_championship_category
from apps.matches.models import MatchEvent
from apps.payments.forms import CardPaymentForm, RegistrationFeeForm, RegistrationPaymentForm
from apps.payments.models import CardPayment, RegistrationAccount, RegistrationAccountNoteHistory, RegistrationFee, RegistrationPayment
from apps.payments.services import configure_registration_fee, register_registration_payment, void_registration_payment
from apps.tournaments.models import Tournament
from apps.users.permissions import can_manage_match, can_manage_tournament

logger = logging.getLogger(__name__)


def _handle_database_contention(request, error):
    if connection.vendor != "sqlite" or "locked" not in str(error).lower():
        raise error
    logger.warning("Registro de inscripción bloqueado por otra operación: %s", error)
    messages.error(request, "Otra operación está usando la base de datos. Inténtalo nuevamente.")


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


def _financial_tournaments(user):
    if user.is_superuser or getattr(user, "role", None) == "ADMIN":
        return Tournament.objects.all()
    if getattr(user, "role", None) == "ORGANIZER":
        return Tournament.objects.filter(organizers=user)
    return Tournament.objects.none()


def _account_or_403(request, account_id):
    account = get_object_or_404(
        RegistrationAccount.objects.select_related("membership__tournament", "membership__team"), pk=account_id,
    )
    return account if can_manage_tournament(request.user, account.membership.tournament) else None


@login_required
def registration_accounts(request):
    if not (request.user.is_superuser or getattr(request.user, "role", None) in {"ADMIN", "ORGANIZER"}):
        return HttpResponseForbidden("No tienes permisos para consultar estas cuentas.")
    tournaments = _financial_tournaments(request.user)
    selected = None
    accounts = []
    selected_id = request.GET.get("tournament")
    if selected_id:
        if not selected_id.isdecimal():
            return HttpResponseBadRequest("Campeonato inválido.")
        selected = get_object_or_404(tournaments, pk=selected_id)
        accounts = list(RegistrationAccount.objects.filter(
            membership__tournament=selected,
            membership__team__name__icontains=request.GET.get("q", "").strip(),
        ).select_related("membership__team", "membership__tournament").prefetch_related("payments"))
        status = request.GET.get("status", "")
        if status in {"PENDIENTE", "PARCIAL", "PAGADO"}:
            accounts = [account for account in accounts if account.payment_status == status]
    return render(request, "payments/registration_accounts.html", {
        "tournaments": tournaments, "selected": selected, "accounts": accounts,
        "fee": RegistrationFee.objects.filter(tournament=selected).first() if selected else None,
        "unconfigured_count": selected.team_memberships.filter(registration_account__isnull=True).count() if selected else 0,
    })


@login_required
def registration_fee(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not can_manage_tournament(request.user, tournament):
        return HttpResponseForbidden("No tienes permisos para administrar este campeonato.")
    fee = RegistrationFee.objects.filter(tournament=tournament).first()
    form = RegistrationFeeForm(request.POST or None, instance=fee, initial={"is_active": True})
    if request.method == "POST" and form.is_valid():
        try:
            configure_registration_fee(tournament, request.user, **form.cleaned_data)
        except OperationalError as error:
            _handle_database_contention(request, error)
            return redirect("registration_fee", tournament_id=tournament.pk)
        else:
            messages.success(request, "Costo configurado. Los importes históricos existentes no se modificaron.")
            return redirect(f"{reverse('registration_accounts')}?tournament={tournament.pk}")
    return render(request, "payments/registration_fee.html", {
        "tournament": tournament, "form": form,
        "history": tournament.registration_fee_history.select_related("created_by").order_by("-created_at", "-pk"),
    })


@login_required
def registration_account(request, account_id):
    account = _account_or_403(request, account_id)
    if account is None:
        return HttpResponseForbidden("No tienes permisos para consultar esta cuenta.")
    form = RegistrationPaymentForm(initial={"payment_date": timezone.localdate(), "submission_id": uuid4()})
    return render(request, "payments/registration_account.html", {
        "account": account, "form": form, "payments": account.payments.select_related("registered_by", "voided_by"),
        "note_history": account.note_history.select_related("created_by").order_by("-created_at", "-pk"),
    })


@login_required
@require_POST
def registration_payment(request, account_id):
    account = _account_or_403(request, account_id)
    if account is None:
        return HttpResponseForbidden("No tienes permisos para administrar esta cuenta.")
    form = RegistrationPaymentForm(request.POST)
    if form.is_valid():
        try:
            register_registration_payment(account, request.user, form.cleaned_data)
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        except OperationalError as error:
            _handle_database_contention(request, error)
        else:
            messages.success(request, "Pago registrado.")
    else:
        messages.error(request, "No se registró el pago: " + "; ".join(
            f"{form.fields[name].label if name in form.fields else 'Pago'}: {', '.join(errors)}"
            for name, errors in form.errors.items()
        ))
    return redirect("registration_account", account_id=account.pk)


@login_required
@require_POST
def registration_payment_void(request, payment_id):
    payment = get_object_or_404(
        RegistrationPayment.objects.select_related("account__membership__tournament"), pk=payment_id,
    )
    if not can_manage_tournament(request.user, payment.account.membership.tournament):
        return HttpResponseForbidden("No tienes permisos para anular este pago.")
    try:
        void_registration_payment(payment, request.user, request.POST.get("reason", ""))
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    except OperationalError as error:
        _handle_database_contention(request, error)
    else:
        messages.success(request, "Pago anulado.")
    return redirect("registration_account", account_id=payment.account_id)


@login_required
@require_POST
def registration_account_notes(request, account_id):
    account = _account_or_403(request, account_id)
    if account is None:
        return HttpResponseForbidden("No tienes permisos para administrar esta cuenta.")
    with transaction.atomic():
        account.notes = request.POST.get("notes", "").strip()
        account.notes_updated_by = request.user
        account.notes_updated_at = timezone.now()
        account.save(update_fields=["notes", "notes_updated_by", "notes_updated_at"])
        RegistrationAccountNoteHistory.objects.create(account=account, notes=account.notes, created_by=request.user)
    messages.success(request, "Observaciones actualizadas.")
    return redirect("registration_account", account_id=account.pk)
