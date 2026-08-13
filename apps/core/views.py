from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.categories import get_request_championship_category
from apps.core.models import APP_CONFIGURATION_METADATA, SOCIAL_LINK_METADATA, AppConfiguration, SocialLink
from apps.teams.models import Player, Team
from apps.users.permissions import organizer_required


def _ensure_configuration_records():
    for key, metadata in APP_CONFIGURATION_METADATA.items():
        AppConfiguration.objects.get_or_create(
            key=key,
            defaults={"is_enabled": metadata.get("default", False)},
        )

    for key, metadata in SOCIAL_LINK_METADATA.items():
        SocialLink.objects.get_or_create(
            key=key,
            defaults={
                "label": metadata.get("label", key),
                "url": "",
                "icon_name": metadata.get("icon", "link"),
            },
        )


@login_required
@organizer_required
def settings_view(request):
    _ensure_configuration_records()

    if request.method == "POST":
        setting_key = request.POST.get("key")
        if setting_key in APP_CONFIGURATION_METADATA:
            setting = AppConfiguration.objects.get(key=setting_key)
            setting.is_enabled = request.POST.get("is_enabled") == "on"
            setting.save(update_fields=["is_enabled", "updated_at"])
            messages.success(request, "Configuracion actualizada correctamente.")
        elif setting_key in SOCIAL_LINK_METADATA:
            social_link = SocialLink.objects.get(key=setting_key)
            social_link.url = request.POST.get("url", "").strip()
            try:
                social_link.full_clean()
                social_link.save(update_fields=["url", "updated_at"])
                messages.success(request, f"Enlace de {social_link.label} actualizado correctamente.")
            except ValidationError:
                messages.error(request, "El enlace ingresado no es válido.")
        return redirect(f"{reverse('settings')}?category={request.GET.get('category', 'seniors')}")

    settings_list = AppConfiguration.objects.all().order_by("key")
    social_links_list = SocialLink.objects.all()
    grouped_settings = {}
    for setting in settings_list:
        group_name = APP_CONFIGURATION_METADATA.get(setting.key, {}).get("group", "general")
        grouped_settings.setdefault(group_name, []).append(setting)

    setting_groups = [
        {
            "key": "general",
            "label": "Configuración general",
            "settings": grouped_settings.get("general", []),
        },
        {
            "key": "player",
            "label": "Configuración de jugadores",
            "settings": grouped_settings.get("player", []),
        },
    ]

    return render(
        request,
        "core/settings.html",
        {
            "settings_list": settings_list,
            "setting_groups": setting_groups,
            "social_links_list": social_links_list,
        },
    )


@login_required
def search_view(request):
    category = get_request_championship_category(request)
    query = (request.GET.get("q") or "").strip()

    teams = Team.objects.none()
    players = Player.objects.none()

    if query:
        teams = Team.objects.filter(category=category).filter(
            Q(name__icontains=query) | Q(coach__icontains=query)
        )
        players = Player.objects.filter(team__category=category).filter(
            Q(name__icontains=query)
            | Q(team__name__icontains=query)
            | Q(ci__icontains=query)
        ).select_related("team")

    return render(
        request,
        "core/search_results.html",
        {
            "query": query,
            "teams": teams[:20],
            "players": players[:30],
            "results_count": teams.count() + players.count() if query else 0,
        },
    )


@login_required
def news_detail_view(request, news_slug):
    news_title = (news_slug or "").replace("-", " ").strip().title() or "Noticia"
    return render(
        request,
        "core/news_detail.html",
        {
            "news_slug": news_slug,
            "news_title": news_title,
        },
    )
