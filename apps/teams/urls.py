from django.urls import path

from apps.teams.views import (
    api_teams,
    player_create_view,
    player_delete_view,
    player_edit_view,
    team_create_view,
    team_delete_view,
    team_detail_view,
    team_edit_view,
    team_manager_settings_view,
    teams_view,
    team_report_view,
)

urlpatterns = [
    path("equipos/", teams_view, name="teams"),
    path("equipos/crear/", team_create_view, name="team_create"),
    path("equipos/<slug:team_slug>/", team_detail_view, name="team"),
    path("equipos/<slug:team_slug>/editar/", team_edit_view, name="team_edit"),
    path("equipos/<slug:team_slug>/configuracion/", team_manager_settings_view, name="team_manager_settings"),
    path("equipos/<slug:team_slug>/eliminar/", team_delete_view, name="team_delete"),
    path("equipos/<slug:team_slug>/reporte/", team_report_view, name="team_report"),
    path("equipos/<slug:team_slug>/jugadores/crear/", player_create_view, name="player_create"),
    path("equipos/<slug:team_slug>/jugadores/<int:player_id>/editar/", player_edit_view, name="player_edit"),
    path("equipos/<slug:team_slug>/jugadores/<int:player_id>/eliminar/", player_delete_view, name="player_delete"),
    path("api/teams/", api_teams, name="api_teams"),
]
