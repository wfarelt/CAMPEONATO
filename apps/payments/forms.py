"""Forms for card payment registration."""

from django import forms

from apps.payments.models import CardPayment


INPUT_CLASS = (
    "w-full rounded-xl border border-[#282e39] bg-[#101622] "
    "px-4 py-3 text-white placeholder:text-[#9da6b9] "
    "focus:border-primary focus:ring-primary"
)


class CardPaymentForm(forms.ModelForm):
    class Meta:
        model = CardPayment
        fields = ["amount", "paid", "paid_date", "notes"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "0", "step": "0.01"}
            ),
            "paid": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded border-[#282e39] bg-[#101622] text-primary"}
            ),
            "paid_date": forms.DateInput(
                attrs={"type": "date", "class": INPUT_CLASS}
            ),
            "notes": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Observaciones opcionales"}
            ),
        }
