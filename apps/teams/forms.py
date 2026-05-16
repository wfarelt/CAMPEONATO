from django import forms

from apps.teams.models import Player, Team


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "coach", "logo"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del equipo"}),
            "coach": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del entrenador"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["name", "ci", "graduation_year", "number", "position"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del jugador"}),
            "ci": forms.TextInput(attrs={"class": "form-control", "placeholder": "Carnet de identidad"}),
            "graduation_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Año de egreso"}),
            "number": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Numero de camiseta"}),
            "position": forms.Select(attrs={"class": "form-control"}),
        }
