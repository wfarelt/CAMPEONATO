from django.http import Http404, HttpResponseForbidden
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date, parse_time

from apps.core.categories import (
    get_request_championship_category,
    get_request_tournament,
    normalize_championship_category,
)
from apps.matches.models import Match
from apps.teams.models import Team
from apps.tournaments.forms import MatchDayForm, MatchFormSet, TournamentForm, get_match_formset_class
from apps.users.permissions import can_manage_tournament, organizer_required
from apps.tournaments.models import MatchDay, Tournament
from apps.tournaments.services import (
    recommend_matches_for_matchday,
    save_matchday_with_matches,
    validate_matchday_teams,
)
from apps.notifications.services import create_and_dispatch_notification
from apps.notifications.models import NotificationAudienceType, NotificationCategory


WIZARD_SESSION_KEY = "create_matchday_wizard"


@login_required
@organizer_required
def tournaments_list(request):
    category = get_request_championship_category(request)
    tournaments = Tournament.objects.filter(category=category, organizers=request.user).order_by("-season", "name")
    return render(
        request,
        "tournaments/tournaments_list.html",
        {"tournaments": tournaments, "selected_category": category},
    )


@login_required
@organizer_required
def tournament_create(request):
    category = get_request_championship_category(request)
    form = TournamentForm(request.POST or None, initial={"category": category})
    if request.method == "POST" and form.is_valid():
        tournament = form.save()
        tournament.organizers.add(request.user)
        tournament.teams.set(form.cleaned_data["teams"])
        return redirect(f"{reverse('tournaments_list')}?category={tournament.category}")
    return render(request, "tournaments/tournament_form.html", {"form": form, "is_edit": False})


@login_required
@organizer_required
def tournament_edit(request, tournament_id):
    category = get_request_championship_category(request)
    tournament = get_object_or_404(
        Tournament,
        pk=tournament_id,
        category=category,
        organizers=request.user,
    )
    form = TournamentForm(request.POST or None, instance=tournament)
    if request.method == "POST" and form.is_valid():
        tournament = form.save()
        tournament.teams.set(form.cleaned_data["teams"])
        return redirect(f"{reverse('tournaments_list')}?category={tournament.category}")
    return render(
        request,
        "tournaments/tournament_form.html",
        {"form": form, "is_edit": True, "tournament": tournament},
    )


def _safe_match_count(value, default=1):
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


def _default_recommended_match_count(category, tournament=None):
    teams = Team.objects.filter(category=category, is_available_for_matchday=True)
    if tournament is not None:
        teams = teams.filter(tournament_memberships__tournament=tournament)
    available_teams_count = teams.count()
    return max(available_teams_count // 2, 1)


def _formset_for_initial(initial_matches, selected_category, tournament=None):
    initial_matches = initial_matches or []
    formset_class = get_match_formset_class(extra=max(1, len(initial_matches)))
    return formset_class(
        initial=initial_matches,
        form_kwargs={"category": selected_category, "tournament": tournament},
    )


def _wizard_state(request):
    return request.session.get(WIZARD_SESSION_KEY, {})


def _save_wizard_state(request, state):
    request.session[WIZARD_SESSION_KEY] = state
    request.session.modified = True


def _clear_wizard_state(request):
    if WIZARD_SESSION_KEY in request.session:
        del request.session[WIZARD_SESSION_KEY]
        request.session.modified = True


def _build_matches_preview(matches_data):
    team_ids = set()
    for match in matches_data:
        team_ids.add(match["home_team"])
        team_ids.add(match["away_team"])

    teams_by_id = Team.objects.in_bulk(team_ids)
    preview = []
    for match in matches_data:
        preview.append(
            {
                "home_team": teams_by_id.get(match["home_team"]),
                "away_team": teams_by_id.get(match["away_team"]),
                "court": match["court"],
                "time": match["time"],
            }
        )
    return preview


@organizer_required
@login_required
def create_matchday(request):
    category = get_request_championship_category(request)
    tournament = get_request_tournament(request, category)
    category_query = f"category={category}"
    if tournament is not None:
        if not can_manage_tournament(request.user, tournament):
            return HttpResponseForbidden("No tienes permisos para administrar esta temporada.")
        category_query += f"&tournament={tournament.pk}"
    state = _wizard_state(request)
    step = request.GET.get("step", "1")

    if request.method == "GET" and request.GET.get("reset") == "1":
        _clear_wizard_state(request)
        state = {}
        step = "1"

    if request.method == "POST":
        step = request.POST.get("step", "1")
        action = request.POST.get("action")

        if action == "cancel":
            _clear_wizard_state(request)
            return redirect(f"{reverse('matchdays_list')}?{category_query}")

        if step == "1":
            form = MatchDayForm(request.POST, user=request.user)
            if form.is_valid():
                normalized_category = normalize_championship_category(form.cleaned_data["category"])
                selected_tournament = form.cleaned_data.get("tournament")
                previous_category = state.get("matchday", {}).get("category")
                state["matchday"] = {
                    "category": normalized_category,
                    "tournament_id": selected_tournament.pk if selected_tournament else None,
                    "date": form.cleaned_data["date"].isoformat(),
                    "description": form.cleaned_data.get("description") or "",
                    "is_visible": form.cleaned_data.get("is_visible", True),
                }
                # If category changes, clear matches to avoid mixed-team categories.
                if previous_category and previous_category != normalized_category:
                    state.pop("matches", None)
                    state.pop("recommended_matches", None)
                _save_wizard_state(request, state)
                next_query = f"category={normalized_category}"
                if selected_tournament:
                    next_query += f"&tournament={selected_tournament.pk}"
                return redirect(f"{reverse('create_matchday')}?step=2&{next_query}")

            return render(
                request,
                "tournaments/create_matchday.html",
                {"step": "1", "matchday_form": form},
            )

        if step == "2":
            if action == "back":
                selected_category = state.get("matchday", {}).get("category", category)
                previous_query = f"category={selected_category}"
                selected_tournament_id = state.get("matchday", {}).get("tournament_id")
                if selected_tournament_id:
                    previous_query += f"&tournament={selected_tournament_id}"
                return redirect(f"{reverse('create_matchday')}?step=1&{previous_query}")

            if "matchday" not in state:
                return redirect(f"{reverse('create_matchday')}?step=1&category={category}")

            selected_category = state["matchday"]["category"]
            selected_tournament = None
            selected_tournament_id = state.get("matchday", {}).get("tournament_id")
            if selected_tournament_id:
                selected_tournament = Tournament.objects.filter(
                    pk=selected_tournament_id,
                    category=selected_category,
                    organizers=request.user,
                ).first()
                if selected_tournament is None:
                    return HttpResponseForbidden("No tienes permisos para administrar esta temporada.")

            if action == "recommend":
                requested_count = _safe_match_count(
                    request.POST.get("recommended_match_count"),
                    default=_default_recommended_match_count(selected_category, selected_tournament),
                )
                recommendation = recommend_matches_for_matchday(
                    selected_category,
                    requested_count,
                    tournament=selected_tournament,
                )
                recommended_matches = recommendation["matches"]
                initial_matches = [
                    {
                        "home_team": item["home_team"],
                        "away_team": item["away_team"],
                    }
                    for item in recommended_matches
                ]
                state["recommended_matches"] = initial_matches
                state["recommended_match_count"] = requested_count
                _save_wizard_state(request, state)

                formset = _formset_for_initial(initial_matches, selected_category, selected_tournament)
                if not recommendation["possible"]:
                    error_message = recommendation["message"] or "No se pueden recomendar partidos sin repetir."
                    if formset.forms:
                        formset.forms[0].add_error(None, error_message)
                    else:
                        formset.non_form_errors()
                return render(
                    request,
                    "tournaments/create_matchday.html",
                    {
                        "step": "2",
                        "formset": formset,
                        "matchday_data": state.get("matchday"),
                        "recommended_match_count": requested_count,
                    },
                )

            formset = MatchFormSet(
                request.POST,
                form_kwargs={"category": selected_category, "tournament": selected_tournament},
            )

            if formset.is_valid():
                matches = []
                for form in formset.forms:
                    cleaned_data = getattr(form, "cleaned_data", None)
                    if not cleaned_data or cleaned_data.get("DELETE"):
                        continue

                    home_team = cleaned_data.get("home_team")
                    away_team = cleaned_data.get("away_team")
                    court = cleaned_data.get("court")
                    time_value = cleaned_data.get("time")
                    if home_team and away_team and court and time_value:
                        matches.append(
                            {
                                "home_team": home_team.id,
                                "away_team": away_team.id,
                                "court": court,
                                "time": time_value.isoformat(),
                            }
                        )

                if not matches:
                    # Add a non-field error to the first form so templates show the message
                    if formset.forms:
                        formset.forms[0].add_error(None, "Debes registrar al menos un partido antes de continuar.")
                    else:
                        # fallback: attach to formset errors object
                        formset.non_form_errors()
                else:
                    state["matches"] = matches
                    state["recommended_matches"] = matches
                    state["recommended_match_count"] = _safe_match_count(
                        request.POST.get("recommended_match_count"),
                        default=state.get(
                            "recommended_match_count",
                            _default_recommended_match_count(selected_category, selected_tournament),
                        ),
                    )
                    _save_wizard_state(request, state)
                    next_query = f"category={selected_category}"
                    if selected_tournament:
                        next_query += f"&tournament={selected_tournament.pk}"
                    return redirect(f"{reverse('create_matchday')}?step=3&{next_query}")

            return render(
                request,
                "tournaments/create_matchday.html",
                {
                    "step": "2",
                    "formset": formset,
                    "matchday_data": state.get("matchday"),
                    "recommended_match_count": _safe_match_count(
                        request.POST.get("recommended_match_count"),
                        default=state.get(
                            "recommended_match_count",
                            _default_recommended_match_count(selected_category, selected_tournament),
                        ),
                    ),
                },
            )

        if step == "3":
            if action == "back":
                selected_category = state.get("matchday", {}).get("category", category)
                previous_query = f"category={selected_category}"
                selected_tournament_id = state.get("matchday", {}).get("tournament_id")
                if selected_tournament_id:
                    previous_query += f"&tournament={selected_tournament_id}"
                return redirect(f"{reverse('create_matchday')}?step=2&{previous_query}")

            if action == "confirm":
                matchday_data = state.get("matchday")
                matches_data = state.get("matches", [])
                if not matchday_data or not matches_data:
                    return redirect(f"{reverse('create_matchday')}?step=1&{category_query}")

                with transaction.atomic():
                    matchday = MatchDay(
                        category=matchday_data["category"],
                        tournament_id=matchday_data.get("tournament_id"),
                        date=parse_date(matchday_data["date"]),
                        description=matchday_data.get("description") or "",
                        is_visible=matchday_data.get("is_visible", True),
                    )
                    matchday.full_clean()
                    validate_matchday_teams(
                        matchday,
                        [
                            team_id
                            for match in matches_data
                            for team_id in (match["home_team"], match["away_team"])
                        ],
                    )
                    matchday.save()
                    for match in matches_data:
                        Match.objects.create(
                            match_day=matchday,
                            home_team_id=match["home_team"],
                            away_team_id=match["away_team"],
                            court=match["court"],
                            time=parse_time(match["time"]),
                            date=matchday.date,
                        )
                    # Crear y despachar notificación push para todos los usuarios
                    detail_url = reverse("matchday_detail", kwargs={"matchday_slug": matchday.slug})
                    push_url = f"{detail_url}?category={matchday.category}"
                    if matchday.tournament_id:
                        push_url += f"&tournament={matchday.tournament_id}"
                    team_ids = set()
                    for home_team_id, away_team_id in matchday.matches.values_list("home_team_id", "away_team_id"):
                        team_ids.update((home_team_id, away_team_id))
                    create_and_dispatch_notification(
                        title="Jornada disponible",
                        message="Nueva Jornada disponible",
                        category=NotificationCategory.MATCH,
                        audience_type=NotificationAudienceType.TEAM,
                        target_teams=Team.objects.filter(pk__in=team_ids),
                        created_by=request.user if hasattr(request, "user") else None,
                        send_push=True,
                        push_url=push_url,
                    )
                _clear_wizard_state(request)
                detail_url = reverse("matchday_detail", kwargs={"matchday_slug": matchday.slug})
                redirect_query = f"category={matchday.category}"
                if matchday.tournament_id:
                    redirect_query += f"&tournament={matchday.tournament_id}"
                return redirect(f"{detail_url}?{redirect_query}")

    if step == "2":
        if "matchday" not in state:
            return redirect(f"{reverse('create_matchday')}?step=1&category={category}")

        selected_category = state["matchday"]["category"]
        matches_initial = state.get("matches") or state.get("recommended_matches")
        selected_tournament_id = state.get("matchday", {}).get("tournament_id")
        selected_tournament = tournament
        if selected_tournament_id and (not selected_tournament or selected_tournament.pk != selected_tournament_id):
            selected_tournament = Tournament.objects.filter(
                pk=selected_tournament_id,
                category=selected_category,
                organizers=request.user,
            ).first()
            if selected_tournament is None:
                return HttpResponseForbidden("No tienes permisos para administrar esta temporada.")
            return render(request, "tournaments/tournaments_list.html", {"tournaments": tournaments, "selected_category": category})
        formset = _formset_for_initial(matches_initial, selected_category, selected_tournament)
        return render(
            request,
            "tournaments/create_matchday.html",
            {
                "step": "2",
                "formset": formset,
                "matchday_data": state.get("matchday"),
                "recommended_match_count": state.get(
                    "recommended_match_count",
                    _default_recommended_match_count(selected_category, selected_tournament),
                ),
            },
        )

    if step == "3":
        matchday_data = state.get("matchday")
        matches_data = state.get("matches", [])
        if not matchday_data:
            return redirect(f"{reverse('create_matchday')}?step=1&category={category}")
        if not matches_data:
            return redirect(f"{reverse('create_matchday')}?step=2&category={matchday_data['category']}")

        return render(
            request,
            "tournaments/create_matchday.html",
            {
                "step": "3",
                "matchday_data": matchday_data,
                "matches_preview": _build_matches_preview(matches_data),
            },
        )

    initial = {"category": category, "tournament": tournament}
    if "matchday" in state:
        matchday_state = state["matchday"]
        initial.update({key: value for key, value in matchday_state.items() if key != "tournament_id"})
        tournament_id = matchday_state.get("tournament_id")
        initial["tournament"] = Tournament.objects.filter(
            pk=tournament_id,
            category=matchday_state.get("category"),
        ).first() if tournament_id else None

    return render(
        request,
        "tournaments/create_matchday.html",
        {
            "step": "1",
            "matchday_form": MatchDayForm(initial=initial, user=request.user),
        },
    )


@organizer_required
@login_required
def edit_matchday(request, matchday_slug):
    category = get_request_championship_category(request)
    tournament = get_request_tournament(request, category)
    if tournament is not None and not can_manage_tournament(request.user, tournament):
        return HttpResponseForbidden("No tienes permisos para administrar esta temporada.")
    matchday_query = MatchDay.objects.filter(slug=matchday_slug, category=category)
    if tournament is not None:
        matchday_query = matchday_query.filter(tournament=tournament)
    if getattr(request.user, "role", None) != "ORGANIZER":
        matchday_query = matchday_query.filter(is_visible=True)
    matchday = get_object_or_404(matchday_query)
    if matchday.tournament_id and not can_manage_tournament(request.user, matchday.tournament):
        return HttpResponseForbidden("No tienes permisos para administrar esta temporada.")

    if request.method == "POST":
        form = MatchDayForm(request.POST, instance=matchday, user=request.user)
        posted_category = normalize_championship_category(request.POST.get("category"))
        posted_tournament = form.fields["tournament"].queryset.filter(
            pk=request.POST.get("tournament") or None,
        ).first()
        formset = MatchFormSet(
            request.POST,
            instance=matchday,
            form_kwargs={"category": posted_category, "tournament": posted_tournament},
        )
        if form.is_valid() and formset.is_valid():
            matchday = save_matchday_with_matches(form, formset)
            detail_url = reverse("matchday_detail", kwargs={"matchday_slug": matchday.slug})
            redirect_query = f"category={matchday.category}"
            if matchday.tournament_id:
                redirect_query += f"&tournament={matchday.tournament_id}"
            return redirect(f"{detail_url}?{redirect_query}")
    else:
        form = MatchDayForm(instance=matchday, user=request.user)
        formset = MatchFormSet(
            instance=matchday,
            form_kwargs={"category": matchday.category, "tournament": matchday.tournament},
        )

    return render(
        request,
        "tournaments/create_matchday.html",
        {"matchday_form": form, "formset": formset, "matchday": matchday, "is_edit": True},
    )


@login_required
def matchday_detail(request, matchday_slug):
    category = get_request_championship_category(request)
    tournament = get_request_tournament(request, category)
    matchday_query = MatchDay.objects.filter(slug=matchday_slug, category=category)
    if tournament is not None:
        matchday_query = matchday_query.filter(tournament=tournament)
    matchday = get_object_or_404(matchday_query)
    matches = Match.objects.filter(match_day=matchday).order_by("court", "time")
    return render(
        request,
        "tournaments/matchday_detail.html",
        {"matchday": matchday, "matches": matches},
    )


@login_required
def matchdays_list(request):
    category = get_request_championship_category(request)
    tournament = get_request_tournament(request, category)
    matchdays = MatchDay.objects.filter(category=category, is_visible=True)
    if tournament is not None:
        matchdays = matchdays.filter(tournament=tournament)
    return render(
        request,
        "tournaments/matchdays_list.html",
        {"matchdays": matchdays, "selected_tournament": tournament},
    )
