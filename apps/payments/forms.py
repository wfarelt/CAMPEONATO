"""Forms for card payment registration."""

from django import forms

from apps.payments.models import CardPayment, RegistrationFee, RegistrationPayment


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


class RegistrationFeeForm(forms.ModelForm):
    class Meta:
        model = RegistrationFee
        fields = ["amount", "notes", "is_active"]
        labels = {"amount": "Costo de inscripción (Bs)", "notes": "Observaciones", "is_active": "Activo"}
        widgets = {
            "amount": forms.NumberInput(attrs={"class": INPUT_CLASS, "min": "0", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class RegistrationPaymentForm(forms.ModelForm):
    submission_id = forms.UUIDField(widget=forms.HiddenInput)

    class Meta:
        model = RegistrationPayment
        fields = ["payment_date", "amount", "method", "receipt_number", "notes"]
        labels = {
            "payment_date": "Fecha de pago", "amount": "Monto (Bs)", "method": "Método de pago",
            "receipt_number": "Comprobante", "notes": "Observaciones",
        }
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "amount": forms.NumberInput(attrs={"class": INPUT_CLASS, "min": "0.01", "step": "0.01"}),
            "method": forms.Select(attrs={"class": INPUT_CLASS}),
            "receipt_number": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "notes": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
        }
