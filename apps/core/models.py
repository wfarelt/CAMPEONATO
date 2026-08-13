"""Core domain models and shared abstractions."""

from django.db import models


TEAM_MANAGER_ENABLE_PLAYERS = "team_manager_enable_players"
TEAM_MANAGER_EDIT_TEAM = "team_manager_edit_team"
ENABLE_PUSH_NOTIFICATIONS = "enable_push_notifications"
PLAYER_FIELD_GRADUATION_YEAR = "player_field_graduation_year"
PLAYER_FIELD_BIRTH_DATE = "player_field_birth_date"
PLAYER_FIELD_PHOTO = "player_field_photo"
PLAYER_FIELD_SUB35 = "player_field_sub35"

SOCIAL_FACEBOOK = "facebook"
SOCIAL_INSTAGRAM = "instagram"
SOCIAL_WHATSAPP = "whatsapp"
SOCIAL_YOUTUBE = "youtube"

APP_CONFIGURATION_CHOICES = [
	(TEAM_MANAGER_ENABLE_PLAYERS, "Permitir que Team Manager habilite jugadores"),
	(TEAM_MANAGER_EDIT_TEAM, "Permitir que Team Manager edite equipo"),
	(ENABLE_PUSH_NOTIFICATIONS, "Habilitar notificaciones push"),
	(PLAYER_FIELD_GRADUATION_YEAR, "Mostrar año de egreso en jugadores"),
	(PLAYER_FIELD_BIRTH_DATE, "Mostrar fecha de nacimiento en jugadores"),
	(PLAYER_FIELD_PHOTO, "Mostrar foto en jugadores"),
	(PLAYER_FIELD_SUB35, "Mostrar campo 'Es Sub35' en jugadores"),
]

SOCIAL_LINK_CHOICES = [
	(SOCIAL_FACEBOOK, "Facebook"),
	(SOCIAL_INSTAGRAM, "Instagram"),
	(SOCIAL_WHATSAPP, "WhatsApp"),
	(SOCIAL_YOUTUBE, "YouTube"),
]

APP_CONFIGURATION_METADATA = {
	TEAM_MANAGER_ENABLE_PLAYERS: {
		"label": "Team Manager puede habilitar jugadores",
		"description": "Permite que el rol Team Manager gestione la habilitacion de jugadores.",
		"default": False,
		"group": "general",
	},
	TEAM_MANAGER_EDIT_TEAM: {
		"label": "Team Manager puede editar equipo",
		"description": "Permite que el rol Team Manager edite entrenador y logo de su equipo asignado.",
		"default": False,
		"group": "general",
	},
	ENABLE_PUSH_NOTIFICATIONS: {
		"label": "Habilitar notificaciones push",
		"description": "Permite enviar notificaciones push a los usuarios (Web Push).",
		"default": True,
		"group": "general",
	},
	PLAYER_FIELD_GRADUATION_YEAR: {
		"label": "Mostrar año de egreso",
		"description": "Activa el campo de año de egreso en el formulario y la vista de jugadores.",
		"default": False,
		"group": "player",
	},
	PLAYER_FIELD_BIRTH_DATE: {
		"label": "Mostrar fecha de nacimiento",
		"description": "Activa el campo de fecha de nacimiento en el formulario y la vista de jugadores.",
		"default": False,
		"group": "player",
	},
	PLAYER_FIELD_PHOTO: {
		"label": "Mostrar foto del jugador",
		"description": "Activa la foto del jugador en el formulario y la vista del equipo.",
		"default": False,
		"group": "player",
	},
	PLAYER_FIELD_SUB35: {
		"label": "Mostrar campo 'Es Sub35'",
		"description": "Activa la marca de jugador Sub35 en el formulario y la vista del equipo.",
		"default": False,
		"group": "player",
	},
}

SITE_BRANDING_DEFAULTS = {
	"league_name": "Super Liga Nacional Florida",
	"league_subtitle": "NACIONAL FLORIDA",
	"primary_color": "#cc0000",
	"secondary_color": "#990000",
	"footer_location_name": "SANTA CRUZ DE LA SIERRA",
	"footer_organizer_name": "PROMO 2001T",
}

SOCIAL_LINK_METADATA = {
	SOCIAL_FACEBOOK: {
		"label": "Facebook",
		"description": "Enlace del perfil o pagina de Facebook.",
		"icon": "facebook",
	},
	SOCIAL_INSTAGRAM: {
		"label": "Instagram",
		"description": "Enlace del perfil de Instagram.",
		"icon": "instagram",
	},
	SOCIAL_WHATSAPP: {
		"label": "WhatsApp",
		"description": "Enlace directo a WhatsApp (wa.me o chat).",
		"icon": "chat",
	},
	SOCIAL_YOUTUBE: {
		"label": "YouTube",
		"description": "Enlace del canal de YouTube.",
		"icon": "smart_display",
	},
}


class AppConfiguration(models.Model):
	key = models.CharField(max_length=80, unique=True, choices=APP_CONFIGURATION_CHOICES)
	is_enabled = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Configuracion"
		verbose_name_plural = "Configuraciones"
		ordering = ["key"]

	def __str__(self):
		return f"{self.key}={'ON' if self.is_enabled else 'OFF'}"

	@property
	def label(self):
		return APP_CONFIGURATION_METADATA.get(self.key, {}).get("label", self.key)

	@property
	def description(self):
		return APP_CONFIGURATION_METADATA.get(self.key, {}).get("description", "")


class SocialLink(models.Model):
	key = models.CharField(max_length=40, unique=True, choices=SOCIAL_LINK_CHOICES)
	label = models.CharField(max_length=60)
	url = models.URLField(blank=True, default="")
	icon_name = models.CharField(max_length=40, default="link")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Red social"
		verbose_name_plural = "Redes sociales"
		ordering = ["key"]

	def __str__(self):
		return f"{self.label}: {self.url or 'sin enlace'}"

	@property
	def description(self):
		return SOCIAL_LINK_METADATA.get(self.key, {}).get("description", "")


class SiteBranding(models.Model):
	league_name = models.CharField(max_length=120, default=SITE_BRANDING_DEFAULTS["league_name"])
	league_subtitle = models.CharField(max_length=120, default=SITE_BRANDING_DEFAULTS["league_subtitle"])
	primary_color = models.CharField(max_length=7, default=SITE_BRANDING_DEFAULTS["primary_color"])
	secondary_color = models.CharField(max_length=7, default=SITE_BRANDING_DEFAULTS["secondary_color"])
	logo = models.ImageField(upload_to="branding/", blank=True, null=True)
	hero_bg_img = models.ImageField(upload_to="branding/", blank=True, null=True)
	footer_location_name = models.CharField(max_length=160, default=SITE_BRANDING_DEFAULTS["footer_location_name"])
	footer_organizer_name = models.CharField(max_length=120, default=SITE_BRANDING_DEFAULTS["footer_organizer_name"])
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Branding de la liga"
		verbose_name_plural = "Branding de la liga"

	def __str__(self):
		return self.league_name

	def save(self, *args, **kwargs):
		self.pk = 1
		super().save(*args, **kwargs)

	@property
	def hero_subtitle(self):
		return self.league_subtitle

	@property
	def has_logo(self):
		return bool(self.logo)

	@property
	def has_hero_bg_img(self):
		return bool(self.hero_bg_img)
