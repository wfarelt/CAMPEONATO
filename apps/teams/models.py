"""Teams domain models."""

from django.conf import settings
from django.db import models

from apps.core.choices import PLAYER_POSITION_CHOICES
from apps.core.categories import CHAMPIONSHIP_CATEGORY_CHOICES, get_championship_label


class Team(models.Model):
	name = models.CharField(max_length=100, unique=True, verbose_name="Team Name")
	coach = models.CharField(max_length=100, verbose_name="Coach Name")
	is_available_for_matchday = models.BooleanField(
		default=True,
		verbose_name="Disponible para jornada",
		help_text="Determina si el equipo puede ser considerado para recomendaciones de partidos.",
	)
	category = models.CharField(
		max_length=20,
		choices=CHAMPIONSHIP_CATEGORY_CHOICES,
		default="seniors",
		verbose_name="Championship Category",
	)
	logo = models.ImageField(upload_to="team_logos/", blank=True, null=True, verbose_name="Team Logo")
	manager = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		limit_choices_to={"role": "TEAM_MANAGER"},
		related_name="managed_teams",
		verbose_name="Manager",
	)

	def __str__(self):
		return f"{self.name} ({get_championship_label(self.category)})"

	class Meta:
		ordering = ["name"]
		verbose_name = "Team"
		verbose_name_plural = "Teams"


class Player(models.Model):
	name = models.CharField(max_length=100, verbose_name="Player Name")
	ci = models.CharField(max_length=20, blank=True, null=True, verbose_name="CI")
	graduation_year = models.PositiveIntegerField(blank=True, null=True, verbose_name="Año de egreso")
	number = models.PositiveIntegerField(verbose_name="Jersey Number")
	position = models.CharField(max_length=2, choices=PLAYER_POSITION_CHOICES, verbose_name="Position")
	goals_scored = models.PositiveIntegerField(default=0, verbose_name="Goles")
	is_reinforcement = models.BooleanField(default=False, verbose_name="Es refuerzo")
	team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players", verbose_name="Team")

	def __str__(self):
		return f"{self.name} ({self.team.name})"
