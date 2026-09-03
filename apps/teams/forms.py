from django import forms
from django.contrib.auth import get_user_model

from apps.core.models import AppConfiguration
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
        fields = [
            "name",
            "ci",
            "graduation_year",
            "birth_date",
            "photo",
            "is_sub35",
            "number",
            "position",
            "is_reinforcement",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del jugador"}),
            "ci": forms.TextInput(attrs={"class": "form-control", "placeholder": "Carnet de identidad"}),
            "graduation_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Año de egreso"}),
            "birth_date": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "number": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Numero de camiseta (opcional)"}),
            "position": forms.Select(attrs={"class": "form-control"}),
            "is_sub35": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_reinforcement": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        config_keys = {
            "graduation_year": "player_field_graduation_year",
            "birth_date": "player_field_birth_date",
            "photo": "player_field_photo",
            "is_sub35": "player_field_sub35",
        }

        for field_name, config_key in config_keys.items():
            if not AppConfiguration.objects.filter(key=config_key, is_enabled=True).exists():
                self.fields.pop(field_name, None)

        self.fields["number"].required = False
