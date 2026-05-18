from django import forms

from apps.notifications.models import (
    Notification,
    NotificationAudienceType,
)


class NotificationCreateForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = [
            "title",
            "message",
            "category",
            "audience_type",
            "role",
            "target_teams",
            "target_users",
            "expires_at",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Titulo de la notificacion"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Mensaje"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "audience_type": forms.Select(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-control"}),
            "target_teams": forms.SelectMultiple(attrs={"class": "form-control", "size": 6}),
            "target_users": forms.SelectMultiple(attrs={"class": "form-control", "size": 6}),
            "expires_at": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        audience_type = cleaned_data.get("audience_type")
        role = cleaned_data.get("role")
        target_teams = cleaned_data.get("target_teams")
        target_users = cleaned_data.get("target_users")

        if audience_type == NotificationAudienceType.ROLE and not role:
            self.add_error("role", "Debes seleccionar un rol para este tipo de audiencia.")

        if audience_type == NotificationAudienceType.TEAM and not target_teams:
            self.add_error("target_teams", "Debes seleccionar al menos un equipo.")

        if audience_type == NotificationAudienceType.USER and not target_users:
            self.add_error("target_users", "Debes seleccionar al menos un usuario.")

        return cleaned_data
