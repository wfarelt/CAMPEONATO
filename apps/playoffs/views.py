from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.categories import get_request_championship_category
from apps.playoffs.forms import PlayoffGenerationForm
from apps.playoffs.models import LeagueSettings, Playoff
from apps.playoffs.services import generate_playoff, get_tie_aggregate
from apps.users.permissions import organizer_required


def playoffs_view(request):
    category = get_request_championship_category(request)
    settings = LeagueSettings.objects.filter(category=category).first()
    playoff = Playoff.objects.filter(category=category, is_active=True).prefetch_related(
        "ties__home_team",
        "ties__away_team",
        "ties__first_leg",
        "ties__second_leg",
    ).first()
    rounds = []
    if playoff:
        ties_by_round = {}
        for tie in playoff.ties.all():
            ties_by_round.setdefault(tie.round, []).append(
                {
                    "tie": tie,
                    "home_goals": get_tie_aggregate(tie)[0],
                    "away_goals": get_tie_aggregate(tie)[1],
                }
            )
        for round_code, round_label in playoff.ties.model.ROUND_CHOICES:
            ties = ties_by_round.get(round_code, [])
            if ties:
                rounds.append({"label": round_label, "ties": ties})
    return render(
        request,
        "playoffs/playoffs.html",
        {
            "settings": settings,
            "playoff": playoff,
            "rounds": rounds,
            "generation_form": PlayoffGenerationForm(),
        },
    )


@organizer_required
def generate_playoff_view(request):
    if request.method != "POST":
        return redirect(reverse("playoffs"))

    category = get_request_championship_category(request)
    form = PlayoffGenerationForm(request.POST)
    if form.is_valid():
        try:
            generate_playoff(category=category, **form.cleaned_data)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            messages.success(request, "El cuadro de playoffs fue generado.")
    else:
        messages.error(request, "Revisa la fecha, hora y cancha para generar el cuadro.")

    return redirect(f"{reverse('playoffs')}?category={category}")