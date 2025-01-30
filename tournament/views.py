from django.shortcuts import render, redirect
from django.db.models import Sum, F, Q
from .models import Team, Player, Match
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

def standings_view(request):
    teams = Team.objects.all()
    standings = []

    for team in teams:
        matches_played = Match.objects.filter(
            Q(home_team=team, status='finished') | Q(away_team=team, status='finished')
        )
        won = matches_played.filter(
            Q(home_team=team, home_score__gt=F('away_score')) | Q(away_team=team, away_score__gt=F('home_score'))
        ).count()
        lost = matches_played.filter(
            Q(home_team=team, home_score__lt=F('away_score')) | Q(away_team=team, away_score__lt=F('home_score'))
        ).count()
        drawn = matches_played.filter(home_score=F('away_score')).count()
        goals_for = matches_played.filter(home_team=team).aggregate(Sum('home_score'))['home_score__sum'] or 0
        goals_for += matches_played.filter(away_team=team).aggregate(Sum('away_score'))['away_score__sum'] or 0
        goals_against = matches_played.filter(home_team=team).aggregate(Sum('away_score'))['away_score__sum'] or 0
        goals_against += matches_played.filter(away_team=team).aggregate(Sum('home_score'))['home_score__sum'] or 0

        standings.append({
            'team': team.name,
            'matches_played': matches_played.count(),
            'won': won,
            'drawn': drawn,
            'lost': lost,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goals_for - goals_against,
            'points': won * 3 + drawn,
        })

    standings = sorted(standings, key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))

    return render(request, 'tournament/standings.html', {'standings': standings})

# Mostrar lista de partidos pendientes

def matches(request):
    matches_pending = Match.objects.filter(status='scheduled')
    matches_finished = Match.objects.filter(status='finished')
    return render(request, 'tournament/matches.html', {'matches_pending': matches_pending, 'matches_finished': matches_finished})