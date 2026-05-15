from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.models import APP_CONFIGURATION_METADATA, AppConfiguration
from apps.users.permissions import organizer_required


@login_required
@organizer_required
def settings_view(request):
    # Ensure known settings exist so future toggles appear automatically.
    for key, metadata in APP_CONFIGURATION_METADATA.items():
        AppConfiguration.objects.get_or_create(
            key=key,
            defaults={"is_enabled": metadata.get("default", False)},
        )

    if request.method == "POST":
        setting_key = request.POST.get("key")
        if setting_key in APP_CONFIGURATION_METADATA:
            setting = AppConfiguration.objects.get(key=setting_key)
            setting.is_enabled = request.POST.get("is_enabled") == "on"
            setting.save(update_fields=["is_enabled", "updated_at"])
            messages.success(request, "Configuracion actualizada correctamente.")
        return redirect(f"{reverse('settings')}?category={request.GET.get('category', 'seniors')}")

    settings_list = AppConfiguration.objects.all()
    return render(request, "core/settings.html", {"settings_list": settings_list})
