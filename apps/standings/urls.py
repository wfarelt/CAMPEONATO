from django.urls import path

from apps.standings.views import standings_api, standings_view, standings_sitemap

urlpatterns = [
    path("tabla-posiciones/", standings_view, name="standings"),
    path("tabla-posiciones/sitemap.xml", standings_sitemap, name="standings_sitemap"),
    path("api/standings/", standings_api, name="standings_api"),
]
