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
    teams_view,
)

urlpatterns = [
    path("teams/", teams_view, name="teams"),
    path("team/create/", team_create_view, name="team_create"),
    path("team/<int:team_id>/", team_detail_view, name="team"),
    path("team/<int:team_id>/edit/", team_edit_view, name="team_edit"),
    path("team/<int:team_id>/delete/", team_delete_view, name="team_delete"),
    path("team/<int:team_id>/players/create/", player_create_view, name="player_create"),
    path("team/<int:team_id>/players/<int:player_id>/edit/", player_edit_view, name="player_edit"),
    path("team/<int:team_id>/players/<int:player_id>/delete/", player_delete_view, name="player_delete"),
    path("api/teams/", api_teams, name="api_teams"),
]
