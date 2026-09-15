from django import forms

from apps.matches.models import Match


class PlayoffGenerationForm(forms.Form):
    match_date = forms.DateField(
        label="Fecha del primer partido",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    match_time = forms.TimeField(
        label="Hora del primer partido",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
    )
    court = forms.ChoiceField(
        label="Cancha",
        choices=Match.COURT_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    second_leg_date = forms.DateField(
        label="Fecha de vuelta",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    second_leg_time = forms.TimeField(
        label="Hora de vuelta",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
    )

    def clean_court(self):
        return int(self.cleaned_data["court"])

    def clean(self):
        cleaned_data = super().clean()
        second_leg_date = cleaned_data.get("second_leg_date")
        second_leg_time = cleaned_data.get("second_leg_time")
        if second_leg_date and not second_leg_time:
            self.add_error("second_leg_time", "Indica la hora de la vuelta.")
        if second_leg_time and not second_leg_date:
            self.add_error("second_leg_date", "Indica la fecha de la vuelta.")
        return cleaned_data