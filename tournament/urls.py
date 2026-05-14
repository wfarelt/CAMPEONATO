from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('teams/', teams, name='teams'),
    path('team/<int:team_id>/', team, name='team'),
    path('standings/', standings_view, name='standings'),
    path('matches/', matches, name='matches'),
        path('statistics/', statistics, name='statistics'),
    # MatchDay URLs
    path('matchday/create/', create_matchday, name='create_matchday'),
    path('matchday/<int:matchday_id>/', matchday_detail, name='matchday_detail'),
    path('matchday/<int:matchday_id>/edit/', edit_matchday, name='edit_matchday'),
    path('matchdays/', matchdays_list, name='matchdays_list'),
    # API endpoints
    path('api/teams/', api_teams, name='api_teams'),
    path('api/standings/', standings_api, name='standings_api'),
]