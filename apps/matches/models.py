"""Matches domain models."""

from django.db import models


class Match(models.Model):
	match_day = models.ForeignKey(
		"tournaments.MatchDay",
		on_delete=models.CASCADE,
		related_name="matches",
		null=True,
		blank=True,
		verbose_name="Match Day",
	)
	home_team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="home_matches")
	away_team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="away_matches")
	home_score = models.PositiveIntegerField(default=0, verbose_name="Home Team Score")
	away_score = models.PositiveIntegerField(default=0, verbose_name="Away Team Score")
	date = models.DateField()
	time = models.TimeField()
	status = models.CharField(
		max_length=20,
		choices=[("scheduled", "Scheduled"), ("finished", "Finished")],
		default="scheduled",
	)

	def __str__(self):
		return f"{self.home_team} vs {self.away_team}"

	@property
	def is_finished(self):
		return self.status == "finished"

	def save(self, *args, **kwargs):
		if self.match_day and not self.date:
			self.date = self.match_day.date
		super().save(*args, **kwargs)


class PointsAdjustment(models.Model):
	team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="points_adjustments")
	match = models.ForeignKey(
		Match,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="points_adjustments",
	)
	points = models.IntegerField(help_text="Puntos sumados o restados (puede ser negativo)")
	reason = models.CharField(max_length=255, help_text="Motivo del ajuste (ej: Observacion, Sancion, etc.)")
	date = models.DateField(auto_now_add=True)

	def __str__(self):
		return f"{self.team.name}: {self.points:+} ({self.reason})"
