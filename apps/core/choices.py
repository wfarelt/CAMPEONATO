"""Reusable choices for models across apps."""

PLAYER_POSITION_CHOICES = [
	("GK", "Arquero"),
	("DF", "Defensa"),
	("MF", "Mediocampista"),
	("FW", "Delantero"),
]

CHAMPIONSHIP_CATEGORY_CHOICES = [
	("seniors", "Seniors"),
	("super_seniors", "Super Seniors"),
]

USER_ROLE_CHOICES = [
	("ADMIN", "Administrador"),
	("ORGANIZER", "Organizador"),
	("TEAM_MANAGER", "Encargado de Equipo"),
	("REFEREE", "Arbitro"),
	("PLAYER", "Jugador"),
]
