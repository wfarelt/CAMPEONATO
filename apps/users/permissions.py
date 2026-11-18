"""Custom permission rules for users app."""

from functools import wraps

from django.http import HttpResponseForbidden


def organizer_required(view_func):
	"""Allow access only to authenticated users with ORGANIZER role."""

	@wraps(view_func)
	def _wrapped(request, *args, **kwargs):
		if getattr(request.user, "role", None) != "ORGANIZER":
			return HttpResponseForbidden("Solo el rol ORGANIZER puede realizar esta accion.")
		return view_func(request, *args, **kwargs)

	return _wrapped


def platform_admin_required(view_func):
	"""Allow access only to platform admins or Django superusers."""
	@wraps(view_func)
	def _wrapped(request, *args, **kwargs):
		if getattr(request.user, "role", None) != "ADMIN" and not getattr(request.user, "is_superuser", False):
			return HttpResponseForbidden("Solo un administrador de plataforma puede realizar esta accion.")
		return view_func(request, *args, **kwargs)

	return _wrapped


def can_manage_tournament(user, tournament):
	"""Return whether the user is authorized to manage this tournament."""
	if not getattr(user, "is_authenticated", False) or tournament is None:
		return False
	if getattr(user, "role", None) == "ADMIN" or getattr(user, "is_superuser", False):
		return True
	return (
		getattr(user, "role", None) == "ORGANIZER"
		and tournament.organizers.filter(pk=user.pk).exists()
	)


def can_manage_match(user, match):
	"""Allow result and event writes only to admins or the match's organizer."""
	if not getattr(user, "is_authenticated", False):
		return False
	if getattr(user, "role", None) == "ADMIN" or getattr(user, "is_superuser", False):
		return True
	if getattr(user, "role", None) != "ORGANIZER":
		return False
	tournament = getattr(match.match_day, "tournament", None) if match.match_day_id else None
	return can_manage_tournament(user, tournament) if tournament else True


def can_manage_players(user):
	"""Return True when user can manage players based on role and app settings."""
	if not getattr(user, "is_authenticated", False):
		return False

	if getattr(user, "role", None) == "ORGANIZER":
		return True

	if getattr(user, "role", None) == "TEAM_MANAGER":
		from apps.core.models import AppConfiguration, TEAM_MANAGER_ENABLE_PLAYERS

		return AppConfiguration.objects.filter(key=TEAM_MANAGER_ENABLE_PLAYERS, is_enabled=True).exists()

	return False


def can_add_players_to_team(user, team):
	"""Return True when user can add players to the provided team."""
	return can_manage_players_for_team(user, team)


def can_manage_players_for_team(user, team):
	"""Return True when user can create, edit or delete players for the provided team."""
	if not can_manage_players(user):
		return False

	if getattr(user, "role", None) == "ORGANIZER":
		return True

	if getattr(user, "role", None) == "TEAM_MANAGER":
		return getattr(team, "manager_id", None) == getattr(user, "id", None)

	return False


def can_manage_team_profile_for_team(user, team):
	"""Return True when user can edit coach/logo for the provided team."""
	if not getattr(user, "is_authenticated", False):
		return False

	if getattr(user, "role", None) != "TEAM_MANAGER":
		return False

	from apps.core.models import AppConfiguration, TEAM_MANAGER_EDIT_TEAM

	if not AppConfiguration.objects.filter(key=TEAM_MANAGER_EDIT_TEAM, is_enabled=True).exists():
		return False

	return getattr(team, "manager_id", None) == getattr(user, "id", None)


def player_management_required(view_func):
	"""Allow access only to users that can manage players."""

	@wraps(view_func)
	def _wrapped(request, *args, **kwargs):
		if not can_manage_players(request.user):
			return HttpResponseForbidden("No tienes permisos para gestionar jugadores.")
		return view_func(request, *args, **kwargs)

	return _wrapped
