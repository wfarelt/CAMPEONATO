from django.urls import path

from apps.core.views import settings_view

urlpatterns = [
    path("settings/", settings_view, name="settings"),
]
