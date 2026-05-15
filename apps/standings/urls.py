from django.urls import path

from apps.standings.views import standings_api, standings_view

urlpatterns = [
    path("standings/", standings_view, name="standings"),
    path("api/standings/", standings_api, name="standings_api"),
]
