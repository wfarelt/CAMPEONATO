from django import forms

from apps.sponsors.models import Sponsor


class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = ["name", "image", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del auspiciador"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
