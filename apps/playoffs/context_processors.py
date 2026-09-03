"""Template context for playoff navigation."""

from apps.core.categories import get_request_championship_category
from apps.playoffs.models import LeagueSettings


def playoffs_context(request):
    category = get_request_championship_category(request)
    return {
        "playoffs_enabled": LeagueSettings.objects.filter(
            category=category,
            playoffs_enabled=True,
        ).exists(),
    }