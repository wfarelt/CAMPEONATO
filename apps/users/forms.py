from django.contrib.auth.forms import UserCreationForm
from django import forms
from apps.teams.models import Team
from .models import User


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Nombre",
        widget=forms.TextInput(attrs={"placeholder": "Tu nombre"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Apellido",
        widget=forms.TextInput(attrs={"placeholder": "Tu apellido"}),
    )
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"placeholder": "correo@ejemplo.com"}),
    )
    favorite_team = forms.ModelChoiceField(
        queryset=Team.objects.all().order_by("name"),
        required=False,
        label="Equipo favorito",
        empty_label="— Sin equipo favorito —",
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "favorite_team", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "PLAYER"
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.favorite_team = self.cleaned_data.get("favorite_team")
        if commit:
            user.save()
        return user
