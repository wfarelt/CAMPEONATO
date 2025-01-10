from django.shortcuts import render, redirect
from .models import Team, Player
# Create your views here.

# home
def home(request):
    return render(request, 'tournament/home.html')

# teams
def teams(request):
    teams = Team.objects.all()
    return render(request, 'tournament/teams.html', {'teams': teams})

def team(request, team_id):
    team = Team.objects.get(pk=team_id)
    return render(request, 'tournament/team.html', {'team': team})