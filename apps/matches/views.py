from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from apps.core.categories import get_request_championship_category
from apps.matches.models import Match
from apps.matches.services import build_home_context, build_matches_context, build_statistics_context


def home(request):
    category = get_request_championship_category(request)
    return render(request, "matches/dashboard.html", build_home_context(category=category))


@login_required
def matches_view(request):
    category = get_request_championship_category(request)
    selected_matchday_slug = request.GET.get("matchday")
    return render(
        request,
        "matches/matches.html",
        build_matches_context(category=category, selected_matchday_slug=selected_matchday_slug),
    )


@login_required
def statistics(request):
    category = get_request_championship_category(request)
    return render(request, "matches/statistics.html", build_statistics_context(category=category))


@login_required
def match_detail_view(request, match_slug):
    category = get_request_championship_category(request)
    match = get_object_or_404(
        Match.objects.select_related("home_team", "away_team", "match_day"),
        slug=match_slug,
        home_team__category=category,
        away_team__category=category,
    )
    return render(request, "matches/match_detail.html", {"match": match})
