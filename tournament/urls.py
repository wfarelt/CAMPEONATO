from django.urls import path
from .views import home, teams, team

urlpatterns = [
    path('', home, name='home'),
    path('teams/', teams, name='teams'),
    path('team/<int:team_id>/', team, name='team'),
]