"""URL patterns for the payments app."""

from django.urls import path

from apps.payments.views import card_payments_list, register_card_payment

urlpatterns = [
    path("pagos/tarjetas/", card_payments_list, name="card_payments"),
    path("pagos/tarjetas/<int:event_id>/pago/", register_card_payment, name="register_card_payment"),
]
