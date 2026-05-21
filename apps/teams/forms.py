from django import forms
from django.contrib.auth import get_user_model

from apps.teams.models import Player, Team

User = get_user_model()


class TeamForm(forms.ModelForm):
    manager = forms.ModelChoiceField(
        queryset=User.objects.filter(role="TEAM_MANAGER").order_by("username"),
        required=False,
        empty_label="Sin manager asignado",
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Manager",
    )

    class Meta:
        model = Team
        fields = ["name", "coach", "logo", "manager", "is_available_for_matchday"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del equipo"}),
            "coach": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del entrenador"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_available_for_matchday": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TeamManagerSettingsForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["coach", "logo"]
        widgets = {
            "coach": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del entrenador"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["name", "ci", "graduation_year", "number", "position", "goals_scored", "is_reinforcement"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del jugador"}),
            "ci": forms.TextInput(attrs={"class": "form-control", "placeholder": "Carnet de identidad"}),
            "graduation_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Año de egreso"}),
            "number": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Numero de camiseta"}),
            "position": forms.Select(attrs={"class": "form-control"}),
            "goals_scored": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Goles anotados", "min": 0}),
            "is_reinforcement": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["goals_scored"].required = False
        self.fields["goals_scored"].initial = self.instance.goals_scored if self.instance.pk else 0
