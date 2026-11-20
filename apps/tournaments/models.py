"""Tournaments domain models."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from apps.core.categories import CHAMPIONSHIP_CATEGORY_CHOICES, get_championship_label


class Tournament(models.Model):
	SETUP = "setup"
	REGISTRATION = "registration"
	IN_PROGRESS = "in_progress"
	COMPLETED = "completed"
	SUSPENDED = "suspended"
	STATUS_CHOICES = [
		(SETUP, "Configuración"),
		(REGISTRATION, "Inscripciones"),
		(IN_PROGRESS, "En curso"),
		(COMPLETED, "Finalizado"),
		(SUSPENDED, "Suspendido"),
	]

	name = models.CharField(max_length=120, verbose_name="Nombre del campeonato")
	season = models.CharField(max_length=50, verbose_name="Temporada")
	category = models.CharField(max_length=20, choices=CHAMPIONSHIP_CATEGORY_CHOICES, default="seniors")
	start_date = models.DateField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SETUP)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	organizers = models.ManyToManyField(
		settings.AUTH_USER_MODEL,
		blank=True,
		related_name="organized_tournaments",
		limit_choices_to={"role": "ORGANIZER"},
		verbose_name="Organizadores autorizados",
	)
	teams = models.ManyToManyField(
		"teams.Team",
		through="TournamentTeam",
		related_name="tournaments",
		blank=True,
		verbose_name="Equipos participantes",
	)

	class Meta:
		ordering = ["-season", "name"]
		constraints = [
			models.UniqueConstraint(
				fields=["name", "season", "category"],
				name="unique_tournament_name_season_category",
			),
		]
		verbose_name = "Campeonato"
		verbose_name_plural = "Campeonatos"

	def __str__(self):
		return f"{self.name} - {self.season} ({get_championship_label(self.category)})"


class ActiveChampionship(models.Model):
	id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
	tournament = models.ForeignKey(Tournament, on_delete=models.PROTECT, related_name="active_home_selections")
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Campeonato activo del sitio"
		verbose_name_plural = "Campeonato activo del sitio"

	def save(self, *args, **kwargs):
		self.pk = 1
		super().save(*args, **kwargs)

	def __str__(self):
		return str(self.tournament)


class TournamentTeam(models.Model):
	tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="team_memberships")
	team = models.ForeignKey("teams.Team", on_delete=models.PROTECT, related_name="tournament_memberships")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["tournament", "team"], name="unique_team_per_tournament"),
		]
		ordering = ["team__name"]
		verbose_name = "Participación de equipo"
		verbose_name_plural = "Participaciones de equipos"

	def clean(self):
		super().clean()
		if self.tournament_id and self.team_id and self.tournament.category != self.team.category:
			raise ValidationError("El equipo debe pertenecer a la misma categoría del campeonato.")

	def __str__(self):
		return f"{self.team} - {self.tournament}"


class TournamentPlayer(models.Model):
	tournament_team = models.ForeignKey(TournamentTeam, on_delete=models.CASCADE, related_name="roster_entries")
	player = models.ForeignKey("teams.Player", on_delete=models.PROTECT, related_name="tournament_roster_entries")
	is_active = models.BooleanField(default=True, verbose_name="Activo en la temporada")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["tournament_team", "player"], name="unique_player_per_tournament_team"),
		]
		ordering = ["player__number", "player__name"]
		verbose_name = "Jugador inscrito en temporada"
		verbose_name_plural = "Jugadores inscritos en temporada"

	def clean(self):
		super().clean()
		if self.tournament_team_id and self.player_id:
			if self.player.team_id != self.tournament_team.team_id:
				raise ValidationError("El jugador debe pertenecer al equipo inscrito en la temporada.")

	def __str__(self):
		return f"{self.player} - {self.tournament_team.tournament}"


class MatchDay(models.Model):
	tournament = models.ForeignKey(
		Tournament,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="matchdays",
		verbose_name="Campeonato",
	)
	category = models.CharField(
		max_length=20,
		choices=CHAMPIONSHIP_CATEGORY_CHOICES,
		default="seniors",
		verbose_name="Championship Category",
	)
	date = models.DateField(verbose_name="Match Day Date")
	slug = models.SlugField(max_length=180, unique=True, blank=True, null=True)
	description = models.TextField(blank=True, null=True, verbose_name="Description")
	is_visible = models.BooleanField(default=True, verbose_name="Visible publicamente")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{get_championship_label(self.category)} - {self.date}"

	def clean(self):
		super().clean()
		if self.tournament_id and self.tournament.category != self.category:
			raise ValidationError({"tournament": "El campeonato debe pertenecer a la misma categoría de la jornada."})

	def _build_unique_slug(self):
		base_text = self.description or f"jornada-{self.date.strftime('%d-%m-%Y')}"
		base_slug = slugify(base_text)[:160] or "jornada"
		slug_candidate = base_slug
		counter = 2
		while MatchDay.objects.exclude(pk=self.pk).filter(slug=slug_candidate).exists():
			slug_candidate = f"{base_slug}-{counter}"[:180]
			counter += 1
		return slug_candidate

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = self._build_unique_slug()
		super().save(*args, **kwargs)

	class Meta:
		ordering = ["-date"]
		constraints = [
			models.UniqueConstraint(
				fields=["category", "date"],
				condition=models.Q(tournament__isnull=True),
				name="unique_legacy_matchday_date_per_category",
			),
			models.UniqueConstraint(
				fields=["tournament", "date"],
				condition=models.Q(tournament__isnull=False),
				name="unique_matchday_date_per_tournament",
			),
		]
		verbose_name = "Match Day"
		verbose_name_plural = "Match Days"
