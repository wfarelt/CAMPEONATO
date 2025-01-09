from django.urls import path
from .views import home, teams

urlpatterns = [
    path('', home, name='home'),
    path('teams/', teams, name='teams'),
]