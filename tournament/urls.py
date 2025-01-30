from django.urls import path
from .views import home, teams, team, standings_view, matches

urlpatterns = [
    path('', home, name='home'),
    path('teams/', teams, name='teams'),
    path('team/<int:team_id>/', team, name='team'),
    path('standings/', standings_view, name='standings'),
    path('matches/', matches, name='matches'),
]