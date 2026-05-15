"""Template context processors for shared UI state."""

from apps.core.categories import (
    CHAMPIONSHIP_CATEGORY_CHOICES,
    get_championship_label,
    get_request_championship_category,
)


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
