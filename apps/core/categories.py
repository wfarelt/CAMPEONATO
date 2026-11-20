"""Shared helpers and constants for championship categories."""

from apps.core.choices import CHAMPIONSHIP_CATEGORY_CHOICES

DEFAULT_CHAMPIONSHIP_CATEGORY = "seniors"


_CATEGORY_LABELS = dict(CHAMPIONSHIP_CATEGORY_CHOICES)


def normalize_championship_category(value):
    """Return a safe category value, falling back to the default."""
    if value in _CATEGORY_LABELS:
        return value
    return DEFAULT_CHAMPIONSHIP_CATEGORY


def get_championship_label(category):
    """Return the display label for a category code."""
    normalized_category = normalize_championship_category(category)
    return _CATEGORY_LABELS[normalized_category]


def can_select_championship(user):
    """Return whether the user may browse seasons and change the active one."""
    return (
        getattr(user, "role", None) in {"ADMIN", "ORGANIZER"}
        or getattr(user, "is_superuser", False)
    )


def get_active_championship():
    """Return the site's configured active championship, if any."""
    from apps.tournaments.models import ActiveChampionship

    active = ActiveChampionship.objects.select_related("tournament").filter(pk=1).first()
    return active.tournament if active else None


def get_request_championship_category(request):
    """Resolve the requested category, defaulting to the site's active championship."""
    active_championship = get_active_championship()
    if not can_select_championship(request.user):
        return active_championship.category if active_championship else DEFAULT_CHAMPIONSHIP_CATEGORY

    raw_category = request.GET.get("category")
    if raw_category is not None:
        return normalize_championship_category(raw_category)
    return active_championship.category if active_championship else DEFAULT_CHAMPIONSHIP_CATEGORY


def get_request_tournament(request, category=None):
    """Resolve an explicit tournament or fall back to the site's active championship."""
    active_championship = get_active_championship()
    if not can_select_championship(request.user):
        if active_championship and (category is None or active_championship.category == category):
            return active_championship
        return None

    if "tournament" not in request.GET:
        if active_championship and (category is None or active_championship.category == category):
            return active_championship
        return None

    tournament_id = request.GET.get("tournament")
    if not tournament_id:
        return None

    from django.http import Http404
    from apps.tournaments.models import Tournament

    if not tournament_id.isdigit():
        raise Http404("El identificador del campeonato no es válido.")

    filters = {"pk": int(tournament_id)}
    if category:
        filters["category"] = category
    try:
        return Tournament.objects.get(**filters)
    except Tournament.DoesNotExist as error:
        raise Http404("No se encontró el campeonato seleccionado.") from error
