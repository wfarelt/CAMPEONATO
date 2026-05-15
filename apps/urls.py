"""Root URL aggregator for all domain apps."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("", include("apps.users.urls")),
    path("", include("apps.matches.urls")),
    path("", include("apps.teams.urls")),
    path("", include("apps.standings.urls")),
    path("", include("apps.tournaments.urls")),
]
