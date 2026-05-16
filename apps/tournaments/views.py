from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date, parse_time

from apps.core.categories import get_request_championship_category, normalize_championship_category
from apps.matches.models import Match
from apps.teams.models import Team
from apps.tournaments.forms import MatchDayForm, MatchFormSet
from apps.tournaments.models import MatchDay
from apps.tournaments.services import save_matchday_with_matches


WIZARD_SESSION_KEY = "create_matchday_wizard"


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
                "time": match["time"],
            }
        )
    return preview


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
            formset = MatchFormSet(request.POST, form_kwargs={"category": selected_category})

            if formset.is_valid():
                matches = []
                for form in formset.forms:
                    cleaned_data = getattr(form, "cleaned_data", None)
                    if not cleaned_data or cleaned_data.get("DELETE"):
                        continue

                    home_team = cleaned_data.get("home_team")
                    away_team = cleaned_data.get("away_team")
                    time_value = cleaned_data.get("time")
                    if home_team and away_team and time_value:
                        matches.append(
                            {
                                "home_team": home_team.id,
                                "away_team": away_team.id,
                                "time": time_value.isoformat(),
                            }
                        )

                if not matches:
                    formset.non_form_errors()
                    formset._non_form_errors = formset.error_class(
                        ["Debes registrar al menos un partido antes de continuar."]
                    )
                else:
                    state["matches"] = matches
                    _save_wizard_state(request, state)
                    return redirect(f"{reverse('create_matchday')}?step=3&category={selected_category}")

            return render(
                request,
                "tournaments/create_matchday.html",
                {
                    "step": "2",
                    "formset": formset,
                    "matchday_data": state.get("matchday"),
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
                            time=parse_time(match["time"]),
                            date=matchday.date,
                        )

                _clear_wizard_state(request)
                detail_url = reverse("matchday_detail", kwargs={"matchday_id": matchday.id})
                return redirect(f"{detail_url}?category={matchday.category}")

    if step == "2":
        if "matchday" not in state:
            return redirect(f"{reverse('create_matchday')}?step=1&category={category}")

        selected_category = state["matchday"]["category"]
        matches_initial = state.get("matches")
        formset = MatchFormSet(initial=matches_initial, form_kwargs={"category": selected_category})
        return render(
            request,
            "tournaments/create_matchday.html",
            {
                "step": "2",
                "formset": formset,
                "matchday_data": state.get("matchday"),
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


@login_required
def edit_matchday(request, matchday_id):
    category = get_request_championship_category(request)
    matchday = get_object_or_404(MatchDay, pk=matchday_id, category=category)

    if request.method == "POST":
        form = MatchDayForm(request.POST, instance=matchday)
        posted_category = normalize_championship_category(request.POST.get("category"))
        formset = MatchFormSet(request.POST, instance=matchday, form_kwargs={"category": posted_category})
        if form.is_valid() and formset.is_valid():
            matchday = save_matchday_with_matches(form, formset)
            detail_url = reverse("matchday_detail", kwargs={"matchday_id": matchday.id})
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
def matchday_detail(request, matchday_id):
    category = get_request_championship_category(request)
    matchday = get_object_or_404(MatchDay, pk=matchday_id, category=category)
    return render(
        request,
        "tournaments/matchday_detail.html",
        {"matchday": matchday, "matches": matchday.matches.all()},
    )


@login_required
def matchdays_list(request):
    category = get_request_championship_category(request)
    return render(request, "tournaments/matchdays_list.html", {"matchdays": MatchDay.objects.filter(category=category)})
