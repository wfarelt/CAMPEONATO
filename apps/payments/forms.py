"""Forms for card payment registration."""

from django import forms

from apps.payments.models import CardPayment


INPUT_CLASS = "form-control bg-dark text-white border-secondary"


class CardPaymentForm(forms.ModelForm):
    class Meta:
        model = CardPayment
        fields = ["amount", "paid", "paid_date", "notes"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "0", "step": "0.01"}
            ),
            "paid": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "paid_date": forms.DateInput(
                attrs={"type": "date", "class": INPUT_CLASS}
            ),
            "notes": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Observaciones opcionales"}
            ),
        }
