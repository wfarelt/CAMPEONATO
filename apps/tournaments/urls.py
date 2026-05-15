from django.urls import path

from apps.tournaments.views import (
    create_matchday,
    edit_matchday,
    matchday_detail,
    matchdays_list,
)

urlpatterns = [
    path("matchday/create/", create_matchday, name="create_matchday"),
    path("matchday/<int:matchday_id>/", matchday_detail, name="matchday_detail"),
    path("matchday/<int:matchday_id>/edit/", edit_matchday, name="edit_matchday"),
    path("matchdays/", matchdays_list, name="matchdays_list"),
]
