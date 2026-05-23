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
					"class": "w-full rounded-xl border border-[#282e39] bg-[#101622] px-4 py-3 text-center text-4xl font-bold text-white placeholder:text-[#9da6b9] focus:border-primary focus:ring-primary",
					"min": 0,
				}
			),
			"away_score": forms.NumberInput(
				attrs={
					"class": "w-full rounded-xl border border-[#282e39] bg-[#101622] px-4 py-3 text-center text-4xl font-bold text-white placeholder:text-[#9da6b9] focus:border-primary focus:ring-primary",
					"min": 0,
				}
			),
			"status": forms.Select(attrs={"class": "w-full rounded-xl border border-gray-300 px-4 py-3"}),
			"court": forms.Select(attrs={"class": "w-full rounded-xl border border-gray-300 px-4 py-3"}),
			"date": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-xl border border-gray-300 px-4 py-3"}),
			"time": forms.TimeInput(attrs={"type": "time", "class": "w-full rounded-xl border border-gray-300 px-4 py-3"}),
		}


class MatchEventForm(forms.ModelForm):
	class Meta:
		model = MatchEvent
		fields = ["player"]
		widgets = {
			"player": forms.Select(attrs={"class": "w-full rounded-xl border border-gray-300 px-4 py-3"}),
		}

	def __init__(self, *args, players=None, **kwargs):
		super().__init__(*args, **kwargs)
		if players is not None:
			self.fields["player"].queryset = players
		else:
			self.fields["player"].queryset = Player.objects.none()
