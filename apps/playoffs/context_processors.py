"""Template context for playoff navigation."""

from apps.core.categories import get_request_championship_category
from apps.playoffs.models import LeagueSettings


def playoffs_context(request):
    category = get_request_championship_category(request)
    is_organizer = getattr(request.user, "role", None) == "ORGANIZER"
    return {
        "playoffs_enabled": is_organizer or LeagueSettings.objects.filter(
            category=category,
            playoffs_enabled=True,
        ).exists(),
    }