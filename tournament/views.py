from django.shortcuts import render, redirect
from django.db.models import Sum, F, Q
from .models import Team, Player, Match
from django.utils import timezone

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



def get_last_results(team, exclude_match=None, n=5):
    # Busca los últimos n partidos terminados del equipo, excluyendo el partido actual si se indica
    matches = Match.objects.filter(
        ((Q(home_team=team) | Q(away_team=team)) & Q(status='finished'))
    )
    if exclude_match:
        matches = matches.exclude(pk=exclude_match.pk)
    matches = matches.order_by('-date', '-time')[:n]
    results = []
    for m in matches:
        if m.home_team == team:
            if m.home_score > m.away_score:
                results.append('G')
            elif m.home_score == m.away_score:
                results.append('E')
            else:
                results.append('P')
        else:
            if m.away_score > m.home_score:
                results.append('G')
            elif m.away_score == m.home_score:
                results.append('E')
            else:
                results.append('P')
    return results

def matches(request):
    matches_pending = Match.objects.filter(status='scheduled').order_by('date', 'time')
    matches_finished = Match.objects.filter(status='finished').order_by('date', 'time')

    matches_pending_list = []
    for match in matches_pending:
        home_logo = match.home_team.logo.url if match.home_team.logo else '/static/tournament/img/default_logo.jpg'
        away_logo = match.away_team.logo.url if match.away_team.logo else '/static/tournament/img/default_logo.jpg'
        matches_pending_list.append({
            'home_team': match.home_team.name,
            'home_team_logo': home_logo,
            'home_team_last_results': get_last_results(match.home_team, exclude_match=match),
            'away_team': match.away_team.name,
            'away_team_logo': away_logo,
            'away_team_last_results': get_last_results(match.away_team, exclude_match=match),
            'date': f"{match.date} {match.time.strftime('%H:%M')}",
        })

    return render(request, 'tournament/matches.html', {
        'matches_pending': matches_pending_list,
        'matches_finished': matches_finished,
    })