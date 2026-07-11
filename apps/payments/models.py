"""Registration and fee payment domain models."""

from django.db import models


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
