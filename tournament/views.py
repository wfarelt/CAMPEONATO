from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, F, Q
from .models import Team, Player, Match, MatchDay
from django.utils import timezone
from django.http import JsonResponse
from .forms import MatchDayForm, MatchFormSet

# Create your views here.

# MatchDay Views
def create_matchday(request):
    """Crear una nueva jornada con múltiples partidos"""
    if request.method == 'POST':
        matchday_form = MatchDayForm(request.POST)
        formset = MatchFormSet(request.POST)
        
        if matchday_form.is_valid() and formset.is_valid():
            matchday = matchday_form.save()
            
            # Guardar los matches sin commitear para asignar fecha primero
            instances = formset.save(commit=False)
            for instance in instances:
                instance.date = matchday.date
                instance.match_day = matchday
                instance.save()
            
            # Manejar deletes
            for obj in formset.deleted_objects:
                obj.delete()
            
            return redirect('matchday_detail', matchday_id=matchday.id)
    else:
        matchday_form = MatchDayForm()
        formset = MatchFormSet()
    
    context = {
        'matchday_form': matchday_form,
        'formset': formset,
    }
    return render(request, 'tournament/create_matchday.html', context)

def edit_matchday(request, matchday_id):
    """Editar una jornada existente"""
    matchday = get_object_or_404(MatchDay, pk=matchday_id)
    
    if request.method == 'POST':
        matchday_form = MatchDayForm(request.POST, instance=matchday)
        formset = MatchFormSet(request.POST, instance=matchday)
        
        if matchday_form.is_valid() and formset.is_valid():
            matchday = matchday_form.save()
            
            # Guardar los matches sin commitear para asignar fecha primero
            instances = formset.save(commit=False)
            for instance in instances:
                instance.date = matchday.date
                instance.match_day = matchday
                instance.save()
            
            # Manejar deletes
            for obj in formset.deleted_objects:
                obj.delete()
            
            return redirect('matchday_detail', matchday_id=matchday.id)
    else:
        matchday_form = MatchDayForm(instance=matchday)
        formset = MatchFormSet(instance=matchday)
    
    context = {
        'matchday_form': matchday_form,
        'formset': formset,
        'matchday': matchday,
        'is_edit': True,
    }
    return render(request, 'tournament/create_matchday.html', context)

def matchday_detail(request, matchday_id):
    """Ver los detalles de una jornada"""
    matchday = get_object_or_404(MatchDay, pk=matchday_id)
    matches = matchday.matches.all()
    
    context = {
        'matchday': matchday,
        'matches': matches,
    }
    return render(request, 'tournament/matchday_detail.html', context)

def matchdays_list(request):
    """Listar todas las jornadas"""
    matchdays = MatchDay.objects.all()
    context = {'matchdays': matchdays}
    return render(request, 'tournament/matchdays_list.html', context)

# home
def home(request):
    latest_matchday = (
        MatchDay.objects
        .prefetch_related('matches__home_team', 'matches__away_team')
        .first()
    )

    timeline_matches = []
    timeline_title = 'Última Jornada'
    featured_match = None

    if latest_matchday and latest_matchday.matches.exists():
        matches_qs = latest_matchday.matches.select_related('home_team', 'away_team').order_by('time')
        timeline_title = latest_matchday.description or f"Jornada del {latest_matchday.date.strftime('%d/%m/%Y')}"
    else:
        latest_match_date = Match.objects.order_by('-date').values_list('date', flat=True).first()
        matches_qs = Match.objects.none()
        if latest_match_date:
            matches_qs = Match.objects.filter(date=latest_match_date).select_related('home_team', 'away_team').order_by('time')
            timeline_title = f"Jornada del {latest_match_date.strftime('%d/%m/%Y')}"

    for match in matches_qs:
        if match.status == 'finished':
            status_label = 'Finalizado'
        else:
            status_label = 'Programado'

        timeline_matches.append({
            'home_team': match.home_team.name,
            'away_team': match.away_team.name,
            'home_short': match.home_team.name[:3].upper(),
            'away_short': match.away_team.name[:3].upper(),
            'home_score': match.home_score if match.status == 'finished' else '-',
            'away_score': match.away_score if match.status == 'finished' else '-',
            'status': status_label,
            'time': match.time.strftime('%H:%M'),
            'is_finished': match.status == 'finished',
        })

    if matches_qs.exists():
        highlighted = matches_qs.filter(status='finished').order_by('-time').first()
        if not highlighted:
            highlighted = matches_qs.order_by('time').first()

        featured_match = {
            'home_team': highlighted.home_team.name,
            'away_team': highlighted.away_team.name,
            'home_logo': highlighted.home_team.logo.url if highlighted.home_team.logo else None,
            'away_logo': highlighted.away_team.logo.url if highlighted.away_team.logo else None,
            'home_score': highlighted.home_score if highlighted.status == 'finished' else '-',
            'away_score': highlighted.away_score if highlighted.status == 'finished' else '-',
            'status': 'FINALIZADO' if highlighted.status == 'finished' else 'PROGRAMADO',
            'status_class': 'text-accent-green bg-accent-green/20' if highlighted.status == 'finished' else 'text-primary bg-primary/20',
            'date': highlighted.date.strftime('%d/%m/%Y'),
            'time': highlighted.time.strftime('%H:%M'),
            'is_finished': highlighted.status == 'finished',
        }

    context = {
        'timeline_title': timeline_title,
        'timeline_matches': timeline_matches,
        'featured_match': featured_match,
    }
    return render(request, 'tournament/dashboard.html', context)

# teams
def teams(request):
    teams = Team.objects.all()
    return render(request, 'tournament/teams.html', {'teams': teams})

def team(request, team_id):
    team = Team.objects.get(pk=team_id)
    next_opponents = get_opponents(team) 
    results = results_by_team(team)   
    context = {
        'team': team,
        'next_opponents': next_opponents,
        'results': results,
    }
    return render(request, 'tournament/team.html', context)

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
        drawn = matches_played.filter(home_score=F('away_score')).count()
        points_from_matches = won * 3 + drawn

        # Suma los ajustes de puntos
        adjustments = team.points_adjustments.aggregate(total=Sum('points'))['total'] or 0
        total_points = points_from_matches + adjustments
        
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
            'lost': matches_played.count() - won - drawn,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goals_for - goals_against,
            'points': total_points,
        })

    standings = sorted(standings, key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))

    return render(request, 'tournament/standings.html', {'standings': standings})

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

def api_teams(request):
    teams = Team.objects.all()
    data = []
    for team in teams:
        data.append({
            'id': team.id,
            'name': team.name,
            'coach': team.coach,
            'logo': team.logo.url if team.logo else None,
        })
    return JsonResponse({'teams': data})

def standings_api(request):
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

    # Ordenar por puntos, diferencia de goles, goles a favor
    standings = sorted(standings, key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))

    return JsonResponse({'standings': standings})

# Funcion que devuelve los equipos con los que no se ha jugado
def get_opponents(team):
    # Todos los equipos menos el propio
    all_teams = set(Team.objects.exclude(pk=team.pk))
    # Equipos con los que ya jugó
    played_matches = Match.objects.filter(
        Q(home_team=team) | Q(away_team=team),
        status='finished'
    )
    already_played = set()
    for match in played_matches:
        if match.home_team == team:
            already_played.add(match.away_team)
        else:
            already_played.add(match.home_team)
    # Equipos con los que falta jugar
    to_play = all_teams - already_played

    # Calcula los puntos de cada equipo con los que falta jugar
    opponents_data = []
    for opp in to_play:
        matches_played = Match.objects.filter(
            Q(home_team=opp, status='finished') | Q(away_team=opp, status='finished')
        )
        won = matches_played.filter(
            Q(home_team=opp, home_score__gt=F('away_score')) | Q(away_team=opp, away_score__gt=F('home_score'))
        ).count()
        drawn = matches_played.filter(home_score=F('away_score')).count()
        points = won * 3 + drawn
        opponents_data.append({
            'team': opp,
            'points': points,
        })

    # Ordena por puntos descendente
    opponents_data = sorted(opponents_data, key=lambda x: -x['points'])

    return opponents_data

# Funcion que devuelva los partidos de un equipo
def results_by_team(team):
    matches = Match.objects.filter(
        Q(home_team=team) | Q(away_team=team),
        status='finished'
    ).order_by('-date', '-time')
    results = []
    for match in matches:
        is_home = match.home_team == team
        opponent = match.away_team if is_home else match.home_team
        goals_for = match.home_score if is_home else match.away_score
        goals_against = match.away_score if is_home else match.home_score
        # Resultado: G=Ganado, E=Empate, P=Perdido
        if goals_for > goals_against:
            result = 'G'
        elif goals_for == goals_against:
            result = 'E'
        else:
            result = 'P'
        results.append({
            'date': match.date,
            'opponent': opponent.name,
            'is_home': is_home,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'result': result,
        })
    return results


def statistics(request):
    """Vista de estadísticas del campeonato"""
    return render(request, 'tournament/statistics.html')