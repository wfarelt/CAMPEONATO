from django import forms
from django.forms import inlineformset_factory

from apps.core.categories import DEFAULT_CHAMPIONSHIP_CATEGORY, normalize_championship_category
from apps.matches.models import Match
from apps.teams.models import Team
from apps.tournaments.models import MatchDay


class MatchDayForm(forms.ModelForm):
    class Meta:
        model = MatchDay
        fields = ["category", "date", "description"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-control"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Ej: Jornada de Apertura, Semifinal, etc."}
            ),
        }


class MatchForm(forms.ModelForm):
    def __init__(self, *args, category=None, **kwargs):
        super().__init__(*args, **kwargs)
        selected_category = normalize_championship_category(category or DEFAULT_CHAMPIONSHIP_CATEGORY)
        teams_qs = Team.objects.filter(category=selected_category).order_by("name")
        self.fields["home_team"].queryset = teams_qs
        self.fields["away_team"].queryset = teams_qs

    class Meta:
        model = Match
        fields = ["home_team", "away_team", "time"]
        widgets = {
            "home_team": forms.Select(attrs={"class": "form-control"}),
            "away_team": forms.Select(attrs={"class": "form-control"}),
            "time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        home_team = cleaned_data.get("home_team")
        away_team = cleaned_data.get("away_team")
        if home_team and away_team and home_team == away_team:
            raise forms.ValidationError("Un equipo no puede jugar contra si mismo.")
        return cleaned_data


MatchFormSet = inlineformset_factory(
    MatchDay,
    Match,
    form=MatchForm,
    extra=1,
    can_delete=True,
)
