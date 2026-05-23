"""Matches domain models."""

from django.db import models
from django.utils.text import slugify


class Match(models.Model):
	COURT_1 = 1
	COURT_2 = 2
	COURT_3 = 3
	COURT_CHOICES = [
		(COURT_1, "Cancha 1"),
		(COURT_2, "Cancha 2"),
		(COURT_3, "Cancha 3"),
	]

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
	slug = models.SlugField(max_length=220, unique=True, blank=True, null=True)
	home_score = models.PositiveIntegerField(default=0, verbose_name="Home Team Score")
	away_score = models.PositiveIntegerField(default=0, verbose_name="Away Team Score")
	court = models.PositiveSmallIntegerField(choices=COURT_CHOICES, default=COURT_1, verbose_name="Cancha")
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

	def _build_unique_slug(self):
		if self.match_day and self.match_day.description:
			matchday_ref = self.match_day.description
		elif self.match_day:
			matchday_ref = f"jornada-{self.match_day.date.strftime('%d-%m-%Y')}"
		else:
			matchday_ref = f"jornada-{self.date.strftime('%d-%m-%Y')}"

		base_text = f"{self.home_team.name}-vs-{self.away_team.name}-{matchday_ref}"
		base_slug = slugify(base_text)[:200] or "partido"
		slug_candidate = base_slug
		counter = 2
		while Match.objects.exclude(pk=self.pk).filter(slug=slug_candidate).exists():
			slug_candidate = f"{base_slug}-{counter}"[:220]
			counter += 1
		return slug_candidate

	def save(self, *args, **kwargs):
		if self.match_day and not self.date:
			self.date = self.match_day.date
		if not self.slug and self.home_team_id and self.away_team_id and self.date:
			self.slug = self._build_unique_slug()
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


class MatchEvent(models.Model):
	GOAL = "goal"
	YELLOW_CARD = "yellow_card"
	RED_CARD = "red_card"
	EVENT_TYPE_CHOICES = [
		(GOAL, "Gol"),
		(YELLOW_CARD, "Tarjeta amarilla"),
		(RED_CARD, "Tarjeta roja"),
	]

	match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="events")
	player = models.ForeignKey("teams.Player", on_delete=models.CASCADE, related_name="match_events")
	team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="match_events")
	event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
	minute = models.PositiveSmallIntegerField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["minute", "id"]

	def __str__(self):
		return f"{self.match}: {self.player} - {self.get_event_type_display()}"

	def save(self, *args, **kwargs):
		if self.player_id and not self.team_id:
			self.team = self.player.team
		super().save(*args, **kwargs)
