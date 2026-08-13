"""Teams domain models."""

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.choices import PLAYER_POSITION_CHOICES
from apps.core.categories import CHAMPIONSHIP_CATEGORY_CHOICES, get_championship_label

PLAYER_FIELD_KEYS = {
    "graduation_year": "player_field_graduation_year",
    "birth_date": "player_field_birth_date",
    "photo": "player_field_photo",
    "is_sub35": "player_field_sub35",
}


def is_player_field_enabled(field_name):
    if field_name not in PLAYER_FIELD_KEYS:
        return False

    from apps.core.models import AppConfiguration

    return AppConfiguration.objects.filter(key=PLAYER_FIELD_KEYS[field_name], is_enabled=True).exists()


class Team(models.Model):
	name = models.CharField(max_length=100, unique=True, verbose_name="Team Name")
	slug = models.SlugField(max_length=160, unique=True, blank=True, null=True)
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

	def _build_unique_slug(self):
		base_slug = slugify(self.name)[:140] or "equipo"
		slug_candidate = base_slug
		counter = 2
		while Team.objects.exclude(pk=self.pk).filter(slug=slug_candidate).exists():
			slug_candidate = f"{base_slug}-{counter}"[:160]
			counter += 1
		return slug_candidate

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = self._build_unique_slug()
		super().save(*args, **kwargs)

	class Meta:
		ordering = ["name"]
		verbose_name = "Team"
		verbose_name_plural = "Teams"


class Player(models.Model):
	name = models.CharField(max_length=100, verbose_name="Player Name")
	ci = models.CharField(max_length=20, blank=True, null=True, verbose_name="CI")
	graduation_year = models.PositiveIntegerField(blank=True, null=True, verbose_name="Año de egreso")
	birth_date = models.DateField(blank=True, null=True, verbose_name="Fecha de nacimiento")
	photo = models.ImageField(upload_to="player_photos/", blank=True, null=True, verbose_name="Foto")
	is_sub35 = models.BooleanField(default=False, verbose_name="Es Sub35")
	number = models.PositiveIntegerField(verbose_name="Jersey Number")
	position = models.CharField(max_length=2, choices=PLAYER_POSITION_CHOICES, verbose_name="Position")
	goals_scored = models.PositiveIntegerField(default=0, verbose_name="Goles")
	is_reinforcement = models.BooleanField(default=False, verbose_name="Es refuerzo")
	team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players", verbose_name="Team")

	@property
	def show_graduation_year(self):
		from apps.core.models import AppConfiguration
		return AppConfiguration.objects.filter(key=PLAYER_FIELD_KEYS["graduation_year"], is_enabled=True).exists()

	@property
	def show_birth_date(self):
		from apps.core.models import AppConfiguration
		return AppConfiguration.objects.filter(key=PLAYER_FIELD_KEYS["birth_date"], is_enabled=True).exists()

	@property
	def show_photo(self):
		from apps.core.models import AppConfiguration
		return AppConfiguration.objects.filter(key=PLAYER_FIELD_KEYS["photo"], is_enabled=True).exists()

	@property
	def show_sub35(self):
		from apps.core.models import AppConfiguration
		return AppConfiguration.objects.filter(key=PLAYER_FIELD_KEYS["is_sub35"], is_enabled=True).exists()

	def __str__(self):
		return f"{self.name} ({self.team.name})"
