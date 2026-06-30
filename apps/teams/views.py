from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Value, When, Q
from django.urls import reverse

from apps.core.categories import get_request_championship_category
from apps.standings.selectors import get_opponents_with_points, get_results_by_team
from apps.teams.forms import PlayerForm, TeamForm, TeamManagerSettingsForm
from apps.teams.models import Player
from apps.matches.models import Match, MatchEvent
from apps.teams.selectors import build_team_api_data, get_all_teams, get_team_or_404
from apps.users.permissions import (
    can_add_players_to_team,
    can_manage_team_profile_for_team,
    can_manage_players_for_team,
    organizer_required,
)


@login_required
def teams_view(request):
    category = get_request_championship_category(request)
    return render(request, "teams/teams.html", {"teams": get_all_teams(category=category)})


@login_required
def team_detail_view(request, team_slug):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_slug, category=category)
    team_players = team.players.annotate(
        position_order=Case(
            When(position="GK", then=Value(0)),
            When(position="DF", then=Value(1)),
            When(position="MF", then=Value(2)),
            When(position="FW", then=Value(3)),
            default=Value(99),
            output_field=IntegerField(),
        )
    ).order_by("position_order", "number", "name")
    context = {
        "team": team,
        "team_players": team_players,
        "next_opponents": get_opponents_with_points(team),
        "results": get_results_by_team(team),
        "can_add_players": can_add_players_to_team(request.user, team),
        "can_edit_team_profile": can_manage_team_profile_for_team(request.user, team),
        "can_edit_players": can_manage_players_for_team(request.user, team),
    }
    return render(request, "teams/team.html", context)


@login_required
def api_teams(request):
    category = get_request_championship_category(request)
    data = [build_team_api_data(t) for t in get_all_teams(category=category)]
    return JsonResponse({"teams": data})


@login_required
@organizer_required
def team_create_view(request):
    category = get_request_championship_category(request)

    if request.method == "POST":
        form = TeamForm(request.POST, request.FILES)
        if form.is_valid():
            team = form.save(commit=False)
            team.category = category
            team.save()
            return redirect(f"{reverse('team', kwargs={'team_slug': team.slug})}?category={category}")
    else:
        form = TeamForm()

    return render(
        request,
        "teams/team_form.html",
        {"form": form, "is_edit": False, "selected_category": category},
    )


@login_required
@organizer_required
def team_edit_view(request, team_slug):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_slug, category=category)

    if request.method == "POST":
        form = TeamForm(request.POST, request.FILES, instance=team)
        if form.is_valid():
            team = form.save()
            return redirect(f"{reverse('team', kwargs={'team_slug': team.slug})}?category={category}")
    else:
        form = TeamForm(instance=team)

    return render(
        request,
        "teams/team_form.html",
        {"form": form, "is_edit": True, "team": team, "selected_category": category},
    )


@login_required
@organizer_required
def team_delete_view(request, team_slug):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_slug, category=category)

    if request.method == "POST":
        team.delete()
        return redirect(f"{reverse('teams')}?category={category}")

    return render(request, "teams/team_confirm_delete.html", {"team": team, "selected_category": category})


@login_required
def team_manager_settings_view(request, team_slug):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_slug, category=category)

    if not can_manage_team_profile_for_team(request.user, team):
        return HttpResponseForbidden("No tienes permisos para editar la configuracion de este equipo.")

    if request.method == "POST":
        form = TeamManagerSettingsForm(request.POST, request.FILES, instance=team)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('team', kwargs={'team_slug': team.slug})}?category={category}")
    else:
        form = TeamManagerSettingsForm(instance=team)

    return render(
        request,
        "teams/team_manager_settings_form.html",
        {"form": form, "team": team, "selected_category": category},
    )


@login_required
def player_create_view(request, team_slug):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_slug, category=category)

    if not can_add_players_to_team(request.user, team):
        return HttpResponseForbidden("No tienes permisos para anadir jugadores a este equipo.")

    if request.method == "POST":
        form = PlayerForm(request.POST)
        if form.is_valid():
            player = form.save(commit=False)
            player.team = team
            player.save()
            return redirect(f"{reverse('team', kwargs={'team_slug': team.slug})}?category={category}")
    else:
        form = PlayerForm()

    return render(
        request,
        "teams/player_form.html",
        {"form": form, "team": team, "is_edit": False},
    )


@login_required
def player_edit_view(request, team_slug, player_id):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_slug, category=category)

    if not can_manage_players_for_team(request.user, team):
        return HttpResponseForbidden("No tienes permisos para editar jugadores de este equipo.")

    player = get_object_or_404(Player, pk=player_id, team=team)

    if request.method == "POST":
        form = PlayerForm(request.POST, instance=player)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('team', kwargs={'team_slug': team.slug})}?category={category}")
    else:
        form = PlayerForm(instance=player)

    return render(
        request,
        "teams/player_form.html",
        {"form": form, "team": team, "player": player, "is_edit": True},
    )


@login_required
def player_delete_view(request, team_slug, player_id):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_slug, category=category)

    if not can_manage_players_for_team(request.user, team):
        return HttpResponseForbidden("No tienes permisos para eliminar jugadores de este equipo.")

    player = get_object_or_404(Player, pk=player_id, team=team)

    if request.method == "POST":
        player.delete()
        return redirect(f"{reverse('team', kwargs={'team_slug': team.slug})}?category={category}")

    return render(
        request,
        "teams/player_confirm_delete.html",
        {"team": team, "player": player},
    )


@login_required
@organizer_required
def team_report_view(request, team_slug):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_slug, category=category)

    # Matches where the team participated (finished only)
    matches = (
        Match.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            home_team__category=category,
            away_team__category=category,
            status="finished",
        )
        .order_by("date", "time")
        .select_related("home_team", "away_team")
    )

    players = team.players.order_by("number", "name").all()

    # Initialize a nested structure: player_id -> match_id -> counters
    stats = {p.id: {m.id: {"goals": 0, "yellow_cards": 0, "red_cards": 0} for m in matches} for p in players}

    # Load all relevant events in one query
    events = (
        MatchEvent.objects.filter(match__in=matches, player__team=team)
        .select_related("player", "match")
    )

    # Totals for the team across listed matches
    totals = {"goals": 0, "yellow_cards": 0, "red_cards": 0}

    for ev in events:
        pid = ev.player_id
        mid = ev.match_id
        if pid in stats and mid in stats[pid]:
            if ev.event_type == MatchEvent.GOAL:
                stats[pid][mid]["goals"] += 1
                totals["goals"] += 1
            elif ev.event_type == MatchEvent.YELLOW_CARD:
                stats[pid][mid]["yellow_cards"] += 1
                totals["yellow_cards"] += 1
            elif ev.event_type == MatchEvent.RED_CARD:
                stats[pid][mid]["red_cards"] += 1
                totals["red_cards"] += 1

    # Build matches list for header display
    matches_info = []
    for m in matches:
        if m.match_day:
            jornada_text = m.match_day.description or f"Jornada {m.match_day.id}"
        else:
            jornada_text = f"Jornada {m.date.strftime('%d/%m/%Y')}"

        jornada_label = f"{jornada_text} - {m.date.strftime('%d/%m/%Y')}"
        # Provide separate labels for home and away so template can break lines
        home_label = f"{m.home_team.name} ({m.home_score})"
        away_label = f"{m.away_team.name} ({m.away_score})"

        matches_info.append({
            "id": m.id,
            "jornada_label": jornada_label,
            "home_label": home_label,
            "away_label": away_label,
            "obj": m,
        })

    # Build per-player rows with ordered cells for template ease
    player_rows = []
    for p in players:
        cells = []
        total_goals = 0
        total_yellow = 0
        total_red = 0
        for m in matches:
            cell = stats.get(p.id, {}).get(m.id, {"goals": 0, "yellow_cards": 0, "red_cards": 0})
            cells.append(cell)
            total_goals += cell.get("goals", 0)
            total_yellow += cell.get("yellow_cards", 0)
            total_red += cell.get("red_cards", 0)
        player_rows.append({
            "player": p,
            "cells": cells,
            "totals": {"goals": total_goals, "yellow_cards": total_yellow, "red_cards": total_red},
        })

    context = {
        "team": team,
        "player_rows": player_rows,
        "matches": matches_info,
        "players": players,  # include original queryset for backwards compatibility
        "totals": totals,
    }

    return render(request, "teams/team_report.html", context)
