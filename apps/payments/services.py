from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.payments.models import RegistrationAccount, RegistrationFee, RegistrationFeeHistory, RegistrationPayment
from apps.payments.signals import create_accounts
from apps.tournaments.models import Tournament, TournamentTeam
from apps.users.permissions import can_manage_tournament


def _authorize(user, tournament):
    if not can_manage_tournament(user, tournament):
        raise PermissionError("No tienes permisos para administrar este campeonato.")


@transaction.atomic
def configure_registration_fee(tournament, user, amount, notes, is_active):
    _authorize(user, tournament)
    # An UPDATE acquires a write lock on SQLite as well as row-locking databases.
    Tournament.objects.filter(pk=tournament.pk).update(id=F("id"))
    fee = RegistrationFee(tournament=tournament, amount=amount, notes=notes, is_active=is_active, updated_by=user)
    fee.full_clean(exclude=["tournament"])
    RegistrationFee.objects.update_or_create(
        tournament=tournament,
        defaults={"amount": amount, "notes": notes, "is_active": is_active, "updated_by": user},
    )
    RegistrationFeeHistory.objects.create(
        tournament=tournament, amount=amount, notes=notes, is_active=is_active, created_by=user,
    )
    if is_active:
        create_accounts(TournamentTeam.objects.filter(tournament=tournament), tournament.pk, created_by=user)


def record_account_creator(tournament, team_ids, user):
    RegistrationAccount.objects.filter(
        membership__tournament=tournament, membership__team_id__in=team_ids, created_by__isnull=True,
    ).update(created_by=user)


@transaction.atomic
def register_registration_payment(account, user, data):
    _authorize(user, account.membership.tournament)
    RegistrationAccount.objects.filter(pk=account.pk).update(id=F("id"))
    account = RegistrationAccount.objects.get(pk=account.pk)
    existing = RegistrationPayment.objects.filter(submission_id=data["submission_id"]).first()
    if existing:
        if existing.account_id != account.pk or existing.registered_by_id != user.pk or any(
            getattr(existing, field) != data[field]
            for field in ("payment_date", "amount", "method", "receipt_number", "notes")
        ):
            raise ValidationError("El identificador de envío ya fue utilizado para otro pago.")
        if existing.voided_at:
            raise ValidationError("El pago de este envío ya fue anulado; registra uno nuevo si corresponde.")
        return existing
    payment = RegistrationPayment(account=account, registered_by=user, **data)
    payment.full_clean()
    if payment.amount > account.balance:
        raise ValidationError("El pago no puede superar el saldo pendiente.")
    payment.save(force_insert=True)
    return payment


@transaction.atomic
def void_registration_payment(payment, user, reason):
    _authorize(user, payment.account.membership.tournament)
    RegistrationAccount.objects.filter(pk=payment.account_id).update(id=F("id"))
    payment.refresh_from_db()
    if payment.voided_at:
        raise ValidationError("El pago ya fue anulado.")
    reason = reason.strip()
    if not reason:
        raise ValidationError("Indica el motivo de la anulación.")
    payment.voided_at = timezone.now()
    payment.voided_by = user
    payment.void_reason = reason
    payment.full_clean()
    payment.save(update_fields=["voided_at", "voided_by", "void_reason"])
