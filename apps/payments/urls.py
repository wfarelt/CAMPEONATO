"""URL patterns for the payments app."""

from django.urls import path

from apps.payments.views import (
    card_payments_list, register_card_payment, registration_accounts, registration_fee,
    registration_account, registration_payment, registration_payment_void, registration_account_notes,
)

urlpatterns = [
    path("pagos/tarjetas/", card_payments_list, name="card_payments"),
    path("pagos/tarjetas/<int:event_id>/pago/", register_card_payment, name="register_card_payment"),
    path("pagos/inscripciones/", registration_accounts, name="registration_accounts"),
    path("pagos/inscripciones/campeonato/<int:tournament_id>/costo/", registration_fee, name="registration_fee"),
    path("pagos/inscripciones/cuenta/<int:account_id>/", registration_account, name="registration_account"),
    path("pagos/inscripciones/cuenta/<int:account_id>/pago/", registration_payment, name="registration_payment"),
    path("pagos/inscripciones/cuenta/<int:account_id>/observaciones/", registration_account_notes, name="registration_account_notes"),
    path("pagos/inscripciones/pago/<int:payment_id>/anular/", registration_payment_void, name="registration_payment_void"),
]
