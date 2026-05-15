
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.choices import USER_ROLE_CHOICES
from .managers import UserManager


class User(AbstractUser):
	role = models.CharField(
		max_length=20,
		choices=USER_ROLE_CHOICES,
		default="PLAYER",
		verbose_name="Role",
	)

	objects = UserManager()

	def is_admin(self):
		return self.role == "ADMIN" or self.is_superuser

	def is_organizer(self):
		return self.role == "ORGANIZER"

	def is_team_manager(self):
		return self.role == "TEAM_MANAGER"

	def is_referee(self):
		return self.role == "REFEREE"

	def is_player(self):
		return self.role == "PLAYER"
