from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date, parse_time

from apps.core.categories import get_request_championship_category, normalize_championship_category
from apps.matches.models import Match
from apps.teams.models import Team
from apps.tournaments.forms import MatchDayForm, MatchFormSet, get_match_formset_class
from apps.users.permissions import organizer_required
from apps.tournaments.models import MatchDay
from apps.tournaments.services import recommend_matches_for_matchday, save_matchday_with_matches
from apps.notifications.services import create_and_dispatch_notification
from apps.notifications.models import NotificationAudienceType, NotificationCategory


WIZARD_SESSION_KEY = "create_matchday_wizard"


def _safe_match_count(value, default=1):
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


def _default_recommended_match_count(category):
    available_teams_count = Team.objects.filter(category=category, is_available_for_matchday=True).count()
    return max(available_teams_count // 2, 1)


def _formset_for_initial(initial_matches, selected_category):
    initial_matches = initial_matches or []
    formset_class = get_match_formset_class(extra=max(1, len(initial_matches)))
    return formset_class(initial=initial_matches, form_kwargs={"category": selected_category})


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
            return redirect(f"{reverse('matchdays_list')}?category={category}")

        if step == "1":
            form = MatchDayForm(request.POST)
            if form.is_valid():
                normalized_category = normalize_championship_category(form.cleaned_data["category"])
                previous_category = state.get("matchday", {}).get("category")
                state["matchday"] = {
                    "category": normalized_category,
                    "date": form.cleaned_data["date"].isoformat(),
                    "description": form.cleaned_data.get("description") or "",
                }
                # If category changes, clear matches to avoid mixed-team categories.
                if previous_category and previous_category != normalized_category:
                    state.pop("matches", None)
                    state.pop("recommended_matches", None)
                _save_wizard_state(request, state)
                return redirect(f"{reverse('create_matchday')}?step=2&category={normalized_category}")

            return render(
                request,
                "tournaments/create_matchday.html",
                {"step": "1", "matchday_form": form},
            )

        if step == "2":
            if action == "back":
                selected_category = state.get("matchday", {}).get("category", category)
                return redirect(f"{reverse('create_matchday')}?step=1&category={selected_category}")

            if "matchday" not in state:
                return redirect(f"{reverse('create_matchday')}?step=1&category={category}")

            selected_category = state["matchday"]["category"]

            if action == "recommend":
                requested_count = _safe_match_count(
                    request.POST.get("recommended_match_count"),
                    default=_default_recommended_match_count(selected_category),
                )
                recommendation = recommend_matches_for_matchday(selected_category, requested_count)
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

                formset = _formset_for_initial(initial_matches, selected_category)
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

            formset = MatchFormSet(request.POST, form_kwargs={"category": selected_category})

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
                            _default_recommended_match_count(selected_category),
                        ),
                    )
                    _save_wizard_state(request, state)
                    return redirect(f"{reverse('create_matchday')}?step=3&category={selected_category}")

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
                            _default_recommended_match_count(selected_category),
                        ),
                    ),
                },
            )

        if step == "3":
            if action == "back":
                selected_category = state.get("matchday", {}).get("category", category)
                return redirect(f"{reverse('create_matchday')}?step=2&category={selected_category}")

            if action == "confirm":
                matchday_data = state.get("matchday")
                matches_data = state.get("matches", [])
                if not matchday_data or not matches_data:
                    return redirect(f"{reverse('create_matchday')}?step=1&category={category}")

                with transaction.atomic():
                    matchday = MatchDay.objects.create(
                        category=matchday_data["category"],
                        date=parse_date(matchday_data["date"]),
                        description=matchday_data.get("description") or "",
                    )
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
                    create_and_dispatch_notification(
                        title="Jornada disponible",
                        message="Nueva Jornada disponible",
                        category=NotificationCategory.MATCH,
                        audience_type=NotificationAudienceType.ALL,
                        created_by=request.user if hasattr(request, "user") else None,
                        send_push=True,
                        push_url=push_url,
                    )
                _clear_wizard_state(request)
                detail_url = reverse("matchday_detail", kwargs={"matchday_slug": matchday.slug})
                return redirect(f"{detail_url}?category={matchday.category}")

    if step == "2":
        if "matchday" not in state:
            return redirect(f"{reverse('create_matchday')}?step=1&category={category}")

        selected_category = state["matchday"]["category"]
        matches_initial = state.get("matches") or state.get("recommended_matches")
        formset = _formset_for_initial(matches_initial, selected_category)
        return render(
            request,
            "tournaments/create_matchday.html",
            {
                "step": "2",
                "formset": formset,
                "matchday_data": state.get("matchday"),
                "recommended_match_count": state.get(
                    "recommended_match_count",
                    _default_recommended_match_count(selected_category),
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

    initial = {"category": category}
    if "matchday" in state:
        initial.update(state["matchday"])

    return render(
        request,
        "tournaments/create_matchday.html",
        {
            "step": "1",
            "matchday_form": MatchDayForm(initial=initial),
        },
    )


@organizer_required
@login_required
def edit_matchday(request, matchday_slug):
    category = get_request_championship_category(request)
    matchday = get_object_or_404(MatchDay, slug=matchday_slug, category=category)

    if request.method == "POST":
        form = MatchDayForm(request.POST, instance=matchday)
        posted_category = normalize_championship_category(request.POST.get("category"))
        formset = MatchFormSet(request.POST, instance=matchday, form_kwargs={"category": posted_category})
        if form.is_valid() and formset.is_valid():
            matchday = save_matchday_with_matches(form, formset)
            detail_url = reverse("matchday_detail", kwargs={"matchday_slug": matchday.slug})
            return redirect(f"{detail_url}?category={matchday.category}")
    else:
        form = MatchDayForm(instance=matchday)
        formset = MatchFormSet(instance=matchday, form_kwargs={"category": matchday.category})

    return render(
        request,
        "tournaments/create_matchday.html",
        {"matchday_form": form, "formset": formset, "matchday": matchday, "is_edit": True},
    )


@login_required
def matchday_detail(request, matchday_slug):
    category = get_request_championship_category(request)
    matchday = get_object_or_404(MatchDay, slug=matchday_slug, category=category)
    matches = Match.objects.filter(match_day=matchday).order_by("court", "time")
    return render(
        request,
        "tournaments/matchday_detail.html",
        {"matchday": matchday, "matches": matches},
    )


@login_required
def matchdays_list(request):
    category = get_request_championship_category(request)
    return render(request, "tournaments/matchdays_list.html", {"matchdays": MatchDay.objects.filter(category=category)})
