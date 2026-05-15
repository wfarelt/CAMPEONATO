"""Standings calculation business logic."""

from apps.standings.selectors import get_sorted_standings


def build_standings(category, include_adjustments=True):
	"""Service entrypoint for standings table generation."""
	return get_sorted_standings(include_adjustments=include_adjustments, category=category)
