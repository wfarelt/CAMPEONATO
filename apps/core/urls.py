from django.urls import path

from apps.core.views import search_view, settings_view

urlpatterns = [
    path("settings/", settings_view, name="settings"),
    path("search/", search_view, name="search"),
]
