"""Teams domain models."""

from django.db import models

from apps.core.choices import PLAYER_POSITION_CHOICES
from apps.core.categories import CHAMPIONSHIP_CATEGORY_CHOICES, get_championship_label


class Team(models.Model):
	name = models.CharField(max_length=100, unique=True, verbose_name="Team Name")
	coach = models.CharField(max_length=100, verbose_name="Coach Name")
	category = models.CharField(
		max_length=20,
		choices=CHAMPIONSHIP_CATEGORY_CHOICES,
		default="seniors",
		verbose_name="Championship Category",
	)
	logo = models.ImageField(upload_to="team_logos/", blank=True, null=True, verbose_name="Team Logo")

	def __str__(self):
		return f"{self.name} ({get_championship_label(self.category)})"

	class Meta:
		ordering = ["name"]
		verbose_name = "Team"
		verbose_name_plural = "Teams"


class Player(models.Model):
	name = models.CharField(max_length=100, verbose_name="Player Name")
	number = models.PositiveIntegerField(verbose_name="Jersey Number")
	position = models.CharField(max_length=2, choices=PLAYER_POSITION_CHOICES, verbose_name="Position")
	team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players", verbose_name="Team")

	def __str__(self):
		return f"{self.name} ({self.team.name})"
