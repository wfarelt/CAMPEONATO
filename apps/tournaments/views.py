from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from apps.core.categories import get_request_championship_category, normalize_championship_category
from apps.tournaments.forms import MatchDayForm, MatchFormSet
from apps.tournaments.models import MatchDay
from apps.tournaments.services import save_matchday_with_matches


@login_required
def create_matchday(request):
    category = get_request_championship_category(request)
    if request.method == "POST":
        form = MatchDayForm(request.POST)
        posted_category = normalize_championship_category(request.POST.get("category"))
        formset = MatchFormSet(request.POST, form_kwargs={"category": posted_category})
        if form.is_valid() and formset.is_valid():
            matchday = save_matchday_with_matches(form, formset)
            detail_url = reverse("matchday_detail", kwargs={"matchday_id": matchday.id})
            return redirect(f"{detail_url}?category={matchday.category}")
    else:
        form = MatchDayForm(initial={"category": category})
        formset = MatchFormSet(form_kwargs={"category": category})

    return render(
        request,
        "tournaments/create_matchday.html",
        {"matchday_form": form, "formset": formset},
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
