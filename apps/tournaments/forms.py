from django import forms
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.core.categories import DEFAULT_CHAMPIONSHIP_CATEGORY, normalize_championship_category
from apps.matches.models import Match
from apps.teams.models import Team
from apps.tournaments.models import MatchDay, Tournament


class MatchDayForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        category = (
            self.data.get(self.add_prefix("category"))
            or self.initial.get("category")
            or getattr(self.instance, "category", None)
        )
        tournaments = Tournament.objects.all()
        if category:
            tournaments = tournaments.filter(category=category)
        if getattr(user, "role", None) == "ORGANIZER":
            tournaments = tournaments.filter(organizers=user)
        self.fields["tournament"].queryset = tournaments.order_by("-season", "name")
        if self.instance.tournament_id:
            self.fields["tournament"].required = True

    class Meta:
        model = MatchDay
        fields = ["category", "tournament", "date", "description", "is_visible"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-control"}),
            "tournament": forms.Select(attrs={"class": "form-control"}),
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Ej: Jornada de Apertura, Semifinal, etc."}
            ),
			"is_visible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TournamentForm(forms.ModelForm):
    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
        label="Equipos participantes",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        category = (
            self.data.get(self.add_prefix("category"))
            or self.initial.get("category")
            or getattr(self.instance, "category", None)
        )
        teams = Team.objects.all()
        if category:
            teams = teams.filter(category=category)
        self.fields["teams"].queryset = teams.order_by("name")
        if self.instance.pk and not self.is_bound:
            self.fields["teams"].initial = self.instance.teams.all()

    class Meta:
        model = Tournament
        fields = ["name", "season", "category", "start_date", "end_date", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "season": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class MatchForm(forms.ModelForm):
    def __init__(self, *args, category=None, tournament=None, **kwargs):
        super().__init__(*args, **kwargs)
        selected_category = normalize_championship_category(category or DEFAULT_CHAMPIONSHIP_CATEGORY)
        teams_qs = Team.objects.filter(category=selected_category, is_available_for_matchday=True)
        if self.instance and self.instance.pk:
            teams_qs = Team.objects.filter(
                Q(category=selected_category, is_available_for_matchday=True)
                | Q(pk__in=[self.instance.home_team_id, self.instance.away_team_id])
            )
        if tournament is not None:
            teams_qs = teams_qs.filter(tournament_memberships__tournament=tournament)
            if self.instance and self.instance.pk:
                teams_qs = teams_qs | Team.objects.filter(pk__in=[self.instance.home_team_id, self.instance.away_team_id])
        teams_qs = teams_qs.order_by("name")
        self.fields["home_team"].queryset = teams_qs
        self.fields["away_team"].queryset = teams_qs

    class Meta:
        model = Match
        fields = ["home_team", "away_team", "court", "time"]
        widgets = {
            "home_team": forms.Select(attrs={"class": "form-control"}),
            "away_team": forms.Select(attrs={"class": "form-control"}),
            "court": forms.Select(attrs={"class": "form-control"}),
            "time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        home_team = cleaned_data.get("home_team")
        away_team = cleaned_data.get("away_team")
        if home_team and away_team and home_team == away_team:
            raise forms.ValidationError("Un equipo no puede jugar contra si mismo.")
        return cleaned_data


class MatchDayMatchFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        assigned_team_ids = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue

            for field_name in ("home_team", "away_team"):
                team = form.cleaned_data.get(field_name)
                if team is None:
                    continue
                if team.pk in assigned_team_ids:
                    raise forms.ValidationError(
                        "Un equipo no puede aparecer en más de un partido de la misma jornada."
                    )
                assigned_team_ids.add(team.pk)


def get_match_formset_class(extra=1):
    return inlineformset_factory(
        MatchDay,
        Match,
        form=MatchForm,
        formset=MatchDayMatchFormSet,
        extra=extra,
        can_delete=True,
    )


MatchFormSet = get_match_formset_class(extra=1)
