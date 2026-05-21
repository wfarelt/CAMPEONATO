from django.urls import path

from apps.tournaments.views import (
    create_matchday,
    edit_matchday,
    matchday_detail,
    matchdays_list,
)

urlpatterns = [
    path("jornadas/crear/", create_matchday, name="create_matchday"),
    path("jornadas/<slug:matchday_slug>/", matchday_detail, name="matchday_detail"),
    path("jornadas/<slug:matchday_slug>/editar/", edit_matchday, name="edit_matchday"),
    path("jornadas/", matchdays_list, name="matchdays_list"),
]
