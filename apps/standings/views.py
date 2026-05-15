from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.core.categories import get_request_championship_category
from apps.standings.services import build_standings


@login_required
def standings_view(request):
    category = get_request_championship_category(request)
    return render(
        request,
        "standings/standings.html",
        {"standings": build_standings(category=category, include_adjustments=True)},
    )


@login_required
def standings_api(request):
    category = get_request_championship_category(request)
    return JsonResponse({"standings": build_standings(category=category, include_adjustments=False)})
