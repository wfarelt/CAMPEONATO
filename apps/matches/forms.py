from django import forms

from apps.matches.models import Match, MatchEvent
from apps.teams.models import Player


class MatchResultForm(forms.ModelForm):
	class Meta:
		model = Match
		fields = ["home_score", "away_score", "status", "court", "date", "time"]
		widgets = {
			"home_score": forms.NumberInput(
				attrs={
					"class": "form-control app-score-input text-center fw-bold",
					"min": 0,
				}
			),
			"away_score": forms.NumberInput(
				attrs={
					"class": "form-control app-score-input text-center fw-bold",
					"min": 0,
				}
			),
			"status": forms.Select(attrs={"class": "form-select"}),
			"court": forms.Select(attrs={"class": "form-select"}),
			"date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
			"time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
		}


class MatchEventForm(forms.ModelForm):
	class Meta:
		model = MatchEvent
		fields = ["player"]
		widgets = {
			"player": forms.Select(attrs={"class": "form-select"}),
		}

	def __init__(self, *args, players=None, **kwargs):
		super().__init__(*args, **kwargs)
		if players is not None:
			self.fields["player"].queryset = players
		else:
			self.fields["player"].queryset = Player.objects.none()
