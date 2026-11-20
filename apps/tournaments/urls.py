from django.urls import path

from apps.tournaments.views import (
    create_matchday,
    edit_matchday,
    matchday_detail,
    matchdays_list,
    set_active_championship,
    tournament_create,
    tournament_edit,
    tournaments_list,
)

urlpatterns = [
    path("campeonatos/activo/", set_active_championship, name="set_active_championship"),
    path("campeonatos/", tournaments_list, name="tournaments_list"),
    path("campeonatos/crear/", tournament_create, name="tournament_create"),
    path("campeonatos/<int:tournament_id>/editar/", tournament_edit, name="tournament_edit"),
    path("jornadas/crear/", create_matchday, name="create_matchday"),
    path("jornadas/<slug:matchday_slug>/", matchday_detail, name="matchday_detail"),
    path("jornadas/<slug:matchday_slug>/editar/", edit_matchday, name="edit_matchday"),
    path("jornadas/", matchdays_list, name="matchdays_list"),
]
