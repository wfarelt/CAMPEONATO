"""Template context for playoff navigation."""

from apps.core.categories import get_request_championship_category, get_request_tournament
from apps.playoffs.models import LeagueSettings


def playoffs_context(request):
    category = get_request_championship_category(request)
    tournament = get_request_tournament(request, category)
    is_organizer = getattr(request.user, "role", None) == "ORGANIZER"
    settings = LeagueSettings.objects.filter(category=category, tournament=tournament).first()
    if settings is None and tournament is not None:
        settings = LeagueSettings.objects.filter(category=category, tournament__isnull=True).first()
    return {
        "playoffs_enabled": is_organizer or bool(settings and settings.playoffs_enabled),
    }