from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.core.categories import get_request_championship_category
from apps.matches.services import build_home_context, build_matches_context, build_statistics_context


@login_required
def home(request):
    category = get_request_championship_category(request)
    return render(request, "matches/dashboard.html", build_home_context(category=category))


@login_required
def matches_view(request):
    category = get_request_championship_category(request)
    return render(request, "matches/matches.html", build_matches_context(category=category))


@login_required
def statistics(request):
    category = get_request_championship_category(request)
    return render(request, "matches/statistics.html", build_statistics_context(category=category))
