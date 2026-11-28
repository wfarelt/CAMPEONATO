"""Registration and fee payment domain models."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum


class CardPayment(models.Model):
    match_event = models.OneToOneField(
        "matches.MatchEvent",
        on_delete=models.CASCADE,
        related_name="card_payment",
        verbose_name="Evento de tarjeta",
    )
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="Monto ($)",
    )
    paid = models.BooleanField(default=False, verbose_name="Pagado")
    paid_date = models.DateField(null=True, blank=True, verbose_name="Fecha de pago")
    notes = models.CharField(max_length=255, blank=True, verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pago de tarjeta"
        verbose_name_plural = "Pagos de tarjetas"
        ordering = ["match_event__team__name", "-match_event__created_at"]

    def __str__(self):
        status = "Pagado" if self.paid else "Pendiente"
        return (
            f"{self.match_event.player} – "
            f"{self.match_event.get_event_type_display()} – "
            f"{self.match_event.team} [{status}]"
        )


class RegistrationFee(models.Model):
    tournament = models.OneToOneField("tournaments.Tournament", on_delete=models.CASCADE, related_name="registration_fee")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gte=0), name="registration_fee_nonnegative")]


class RegistrationFeeHistory(models.Model):
    tournament = models.ForeignKey("tournaments.Tournament", on_delete=models.PROTECT, related_name="registration_fee_history")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class RegistrationAccount(models.Model):
    membership = models.OneToOneField("tournaments.TournamentTeam", on_delete=models.CASCADE, related_name="registration_account")
    agreed_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    registered_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="created_registration_accounts",
    )
    notes = models.TextField(blank=True)
    notes_updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    notes_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(agreed_amount__gte=0), name="registration_account_nonnegative")]

    @property
    def total_paid(self):
        if "payments" in getattr(self, "_prefetched_objects_cache", {}):
            return sum((payment.amount for payment in self.payments.all() if payment.voided_at is None), Decimal("0"))
        return self.payments.filter(voided_at__isnull=True).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    @property
    def balance(self):
        return self.agreed_amount - self.total_paid

    @property
    def percentage_paid(self):
        if not self.agreed_amount:
            return Decimal("100")
        return self.total_paid * 100 / self.agreed_amount

    @property
    def payment_status(self):
        paid = self.total_paid
        if paid > self.agreed_amount:
            return "A FAVOR"
        if paid >= self.agreed_amount:
            return "PAGADO"
        return "PENDIENTE" if paid == 0 else "PARCIAL"


class RegistrationAccountNoteHistory(models.Model):
    account = models.ForeignKey(RegistrationAccount, on_delete=models.CASCADE, related_name="note_history")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class RegistrationPaymentQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Los pagos de inscripción no se eliminan; deben anularse.")


class RegistrationPayment(models.Model):
    CASH = "cash"
    TRANSFER = "transfer"
    OTHER = "other"
    METHOD_CHOICES = [(CASH, "Efectivo"), (TRANSFER, "Transferencia"), (OTHER, "Otro")]

    account = models.ForeignKey(RegistrationAccount, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    receipt_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    submission_id = models.UUIDField(unique=True, editable=False)
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="registration_payments")
    created_at = models.DateTimeField(auto_now_add=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="voided_registration_payments")
    void_reason = models.TextField(blank=True)
    objects = RegistrationPaymentQuerySet.as_manager()

    class Meta:
        ordering = ["-payment_date", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="registration_payment_positive"),
            models.CheckConstraint(
                condition=(models.Q(voided_at__isnull=True, voided_by__isnull=True, void_reason="")
                           | (models.Q(voided_at__isnull=False, voided_by__isnull=False) & ~models.Q(void_reason=""))),
                name="registration_payment_void_consistent",
            ),
        ]

    def delete(self, *args, **kwargs):
        raise ValidationError("Los pagos de inscripción no se eliminan; deben anularse.")
