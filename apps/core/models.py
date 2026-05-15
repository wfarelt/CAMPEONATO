"""Core domain models and shared abstractions."""

from django.db import models


TEAM_MANAGER_ENABLE_PLAYERS = "team_manager_enable_players"

APP_CONFIGURATION_CHOICES = [
	(TEAM_MANAGER_ENABLE_PLAYERS, "Permitir que Team Manager habilite jugadores"),
]

APP_CONFIGURATION_METADATA = {
	TEAM_MANAGER_ENABLE_PLAYERS: {
		"label": "Team Manager puede habilitar jugadores",
		"description": "Permite que el rol Team Manager gestione la habilitacion de jugadores.",
		"default": False,
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
