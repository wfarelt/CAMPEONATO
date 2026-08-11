"""Core domain models and shared abstractions."""

from django.db import models


TEAM_MANAGER_ENABLE_PLAYERS = "team_manager_enable_players"
TEAM_MANAGER_EDIT_TEAM = "team_manager_edit_team"
ENABLE_PUSH_NOTIFICATIONS = "enable_push_notifications"

SOCIAL_FACEBOOK = "facebook"
SOCIAL_INSTAGRAM = "instagram"
SOCIAL_WHATSAPP = "whatsapp"
SOCIAL_YOUTUBE = "youtube"

APP_CONFIGURATION_CHOICES = [
	(TEAM_MANAGER_ENABLE_PLAYERS, "Permitir que Team Manager habilite jugadores"),
	(TEAM_MANAGER_EDIT_TEAM, "Permitir que Team Manager edite equipo"),
	(ENABLE_PUSH_NOTIFICATIONS, "Habilitar notificaciones push"),
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
	},
	TEAM_MANAGER_EDIT_TEAM: {
		"label": "Team Manager puede editar equipo",
		"description": "Permite que el rol Team Manager edite entrenador y logo de su equipo asignado.",
		"default": False,
	},
	ENABLE_PUSH_NOTIFICATIONS: {
		"label": "Habilitar notificaciones push",
		"description": "Permite enviar notificaciones push a los usuarios (Web Push).",
		"default": True,
	},
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
