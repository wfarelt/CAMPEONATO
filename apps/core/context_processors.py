"""Template context processors for shared UI state."""

from django.templatetags.static import static

from apps.core.categories import (
    CHAMPIONSHIP_CATEGORY_CHOICES,
    get_championship_label,
    get_request_championship_category,
    get_request_tournament,
)
from apps.core.models import SOCIAL_LINK_METADATA, SiteBranding, SocialLink
from apps.tournaments.models import Tournament


def championship_context(request):
    """Expose selected championship category across all templates."""
    selected_category = get_request_championship_category(request)
    selected_tournament = get_request_tournament(request, selected_category)
    tournament_query = f"category={selected_category}"
    if selected_tournament:
        tournament_query += f"&tournament={selected_tournament.pk}"
    return {
        "championship_category": selected_category,
        "championship_category_label": get_championship_label(selected_category),
        "selected_tournament": selected_tournament,
        "championship_tournaments": Tournament.objects.filter(category=selected_category).order_by("-season", "name"),
        "tournament_query": tournament_query,
        "championship_categories": [
            {"value": value, "label": label}
            for value, label in CHAMPIONSHIP_CATEGORY_CHOICES
        ],
        "category_query": tournament_query,
    }


def social_links_context(request):
    """Expose configured social links across all templates."""
    configured_links = {link.key: link for link in SocialLink.objects.all()}
    return {
        "social_links": {
            key: {
                "label": metadata.get("label", key),
                "description": metadata.get("description", ""),
                "icon_name": metadata.get("icon", "link"),
                "url": configured_links.get(key).url if configured_links.get(key) else "",
            }
            for key, metadata in SOCIAL_LINK_METADATA.items()
        }
    }


def site_branding_context(request):
    """Expose global league branding across all templates."""
    branding = SiteBranding.objects.first() or SiteBranding()
    branding.logo_url = branding.logo.url if branding.logo else static("tournament/img/cnf4.png")
    branding.hero_background_url = branding.hero_bg_img.url if branding.hero_bg_img else static("tournament/img/hero.png")
    return {"site_branding": branding}
