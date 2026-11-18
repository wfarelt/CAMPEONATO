from django import forms

from apps.matches.models import Match
from apps.playoffs.models import LeagueSettings


class PlayoffSettingsForm(forms.ModelForm):
    class Meta:
        model = LeagueSettings
        fields = [
            "teams_classified",
            "playoffs_enabled",
            "third_place_match",
            "playoffs_home_and_away",
            "final_home_and_away",
            "penalties_on_aggregate_tie",
            "sporting_advantage_on_tie",
            "replay_on_aggregate_tie",
        ]
        labels = {
            "teams_classified": "Equipos clasificados",
            "playoffs_enabled": "Habilitar playoffs",
            "third_place_match": "Incluir partido por el tercer puesto",
            "playoffs_home_and_away": "Rondas a ida y vuelta",
            "final_home_and_away": "Final a ida y vuelta",
            "penalties_on_aggregate_tie": "Resolver empate global por penales",
            "sporting_advantage_on_tie": "Usar ventaja deportiva en empate",
            "replay_on_aggregate_tie": "Permitir partido de desempate",
        }
        widgets = {
            "teams_classified": forms.NumberInput(attrs={"class": "form-control", "min": 2, "max": 64, "step": 1}),
            "playoffs_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "third_place_match": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "playoffs_home_and_away": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "final_home_and_away": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "penalties_on_aggregate_tie": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sporting_advantage_on_tie": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "replay_on_aggregate_tie": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


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


class PlayoffPenaltiesForm(forms.Form):
    home_penalties = forms.IntegerField(
        label="Penales del equipo local",
        min_value=0,
        widget=forms.NumberInput(attrs={"min": 0, "class": "form-control", "placeholder": "0"}),
    )
    away_penalties = forms.IntegerField(
        label="Penales del equipo visitante",
        min_value=0,
        widget=forms.NumberInput(attrs={"min": 0, "class": "form-control", "placeholder": "0"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        home_penalties = cleaned_data.get("home_penalties")
        away_penalties = cleaned_data.get("away_penalties")
        if home_penalties is not None and home_penalties == away_penalties:
            raise forms.ValidationError("Los penales deben dejar un ganador.")
        return cleaned_data


class PlayoffRoundScheduleForm(forms.Form):
    SINGLE = "single"
    HOME_AND_AWAY = "home_and_away"

    match_date = forms.DateField(
        label="Fecha de ida / partido único",
        widget=forms.DateInput(attrs={"type": "date", "class": "w-full rounded-xl border border-[#282e39] bg-[#101622] px-4 py-3 text-white"}),
    )
    match_time = forms.TimeField(
        label="Hora",
        widget=forms.TimeInput(attrs={"type": "time", "class": "w-full rounded-xl border border-[#282e39] bg-[#101622] px-4 py-3 text-white"}),
    )
    court = forms.ChoiceField(
        label="Cancha",
        choices=Match.COURT_CHOICES,
        widget=forms.Select(attrs={"class": "w-full rounded-xl border border-[#282e39] bg-[#101622] px-4 py-3 text-white"}),
    )
    format = forms.ChoiceField(
        label="Formato de la llave",
        choices=[(SINGLE, "Partido único"), (HOME_AND_AWAY, "Ida y vuelta")],
        widget=forms.Select(attrs={"class": "w-full rounded-xl border border-[#282e39] bg-[#101622] px-4 py-3 text-white"}),
    )
    second_leg_date = forms.DateField(
        label="Fecha de vuelta",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "w-full rounded-xl border border-[#282e39] bg-[#101622] px-4 py-3 text-white"}),
    )
    second_leg_time = forms.TimeField(
        label="Hora de vuelta",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": "w-full rounded-xl border border-[#282e39] bg-[#101622] px-4 py-3 text-white"}),
    )

    def clean_court(self):
        return int(self.cleaned_data["court"])

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("format") == self.HOME_AND_AWAY:
            if not cleaned_data.get("second_leg_date"):
                self.add_error("second_leg_date", "Indica la fecha de vuelta.")
            if not cleaned_data.get("second_leg_time"):
                self.add_error("second_leg_time", "Indica la hora de vuelta.")
        return cleaned_data