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


def get_request_championship_category(request):
    """Resolve selected category from query string in HTTP requests."""
    raw_category = request.GET.get("category")
    return normalize_championship_category(raw_category)


def get_request_tournament(request, category=None):
    """Return the selected tournament or reject malformed/cross-category IDs."""
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
