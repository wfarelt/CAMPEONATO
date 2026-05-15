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
