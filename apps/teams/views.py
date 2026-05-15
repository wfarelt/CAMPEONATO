from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from apps.core.categories import get_request_championship_category
from apps.standings.selectors import get_opponents_with_points, get_results_by_team
from apps.teams.forms import PlayerForm, TeamForm
from apps.teams.models import Player
from apps.teams.selectors import build_team_api_data, get_all_teams, get_team_or_404
from apps.users.permissions import can_manage_players, organizer_required, player_management_required


@login_required
def teams_view(request):
    category = get_request_championship_category(request)
    return render(request, "teams/teams.html", {"teams": get_all_teams(category=category)})


@login_required
def team_detail_view(request, team_id):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_id, category=category)
    context = {
        "team": team,
        "next_opponents": get_opponents_with_points(team),
        "results": get_results_by_team(team),
        "can_manage_players": can_manage_players(request.user),
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
            return redirect(f"{reverse('team', kwargs={'team_id': team.id})}?category={category}")
    else:
        form = TeamForm()

    return render(
        request,
        "teams/team_form.html",
        {"form": form, "is_edit": False, "selected_category": category},
    )


@login_required
@organizer_required
def team_edit_view(request, team_id):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_id, category=category)

    if request.method == "POST":
        form = TeamForm(request.POST, request.FILES, instance=team)
        if form.is_valid():
            team = form.save()
            return redirect(f"{reverse('team', kwargs={'team_id': team.id})}?category={category}")
    else:
        form = TeamForm(instance=team)

    return render(
        request,
        "teams/team_form.html",
        {"form": form, "is_edit": True, "team": team, "selected_category": category},
    )


@login_required
@organizer_required
def team_delete_view(request, team_id):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_id, category=category)

    if request.method == "POST":
        team.delete()
        return redirect(f"{reverse('teams')}?category={category}")

    return render(request, "teams/team_confirm_delete.html", {"team": team, "selected_category": category})


@login_required
@player_management_required
def player_create_view(request, team_id):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_id, category=category)

    if request.method == "POST":
        form = PlayerForm(request.POST)
        if form.is_valid():
            player = form.save(commit=False)
            player.team = team
            player.save()
            return redirect(f"{reverse('team', kwargs={'team_id': team.id})}?category={category}")
    else:
        form = PlayerForm()

    return render(
        request,
        "teams/player_form.html",
        {"form": form, "team": team, "is_edit": False},
    )


@login_required
@player_management_required
def player_edit_view(request, team_id, player_id):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_id, category=category)
    player = get_object_or_404(Player, pk=player_id, team=team)

    if request.method == "POST":
        form = PlayerForm(request.POST, instance=player)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('team', kwargs={'team_id': team.id})}?category={category}")
    else:
        form = PlayerForm(instance=player)

    return render(
        request,
        "teams/player_form.html",
        {"form": form, "team": team, "player": player, "is_edit": True},
    )


@login_required
@player_management_required
def player_delete_view(request, team_id, player_id):
    category = get_request_championship_category(request)
    team = get_team_or_404(team_id, category=category)
    player = get_object_or_404(Player, pk=player_id, team=team)

    if request.method == "POST":
        player.delete()
        return redirect(f"{reverse('team', kwargs={'team_id': team.id})}?category={category}")

    return render(
        request,
        "teams/player_confirm_delete.html",
        {"team": team, "player": player},
    )
