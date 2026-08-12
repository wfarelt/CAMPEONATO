"""Template context processors for shared UI state."""

from django.templatetags.static import static

from apps.core.categories import (
    CHAMPIONSHIP_CATEGORY_CHOICES,
    get_championship_label,
    get_request_championship_category,
)
from apps.core.models import SOCIAL_LINK_METADATA, SiteBranding, SocialLink


def championship_context(request):
    """Expose selected championship category across all templates."""
    selected_category = get_request_championship_category(request)
    return {
        "championship_category": selected_category,
        "championship_category_label": get_championship_label(selected_category),
        "championship_categories": [
            {"value": value, "label": label}
            for value, label in CHAMPIONSHIP_CATEGORY_CHOICES
        ],
        "category_query": f"category={selected_category}",
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
