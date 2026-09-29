from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.categories import get_request_championship_category
from apps.playoffs.forms import PlayoffGenerationForm, PlayoffPenaltiesForm, PlayoffRoundScheduleForm
from apps.playoffs.models import LeagueSettings, Playoff, PlayoffMatch, PlayoffTie
from apps.playoffs.services import (
    generate_playoff,
    get_tie_match,
    get_tie_matches,
    get_tie_points,
    get_next_schedulable_round,
    record_penalty_result,
    schedule_playoff_round,
    sync_playoff_advancement,
)
from apps.users.permissions import organizer_required

ROUND_SCHEDULE_LABELS = {
    PlayoffTie.ROUND_OF_16: "octavos de final",
    PlayoffTie.QUARTERFINAL: "cuartos de final",
    PlayoffTie.SEMIFINAL: "semifinales",
    PlayoffTie.FINAL: "final",
}


def playoffs_view(request):
    category = get_request_championship_category(request)
    settings = LeagueSettings.objects.filter(category=category).first()
    playoff = Playoff.objects.filter(category=category, is_active=True).select_related("settings").prefetch_related(
        "ties__home_team",
        "ties__away_team",
        "ties__match_links__match",
    ).first()
    rounds = []
    if playoff:
        # Recover old brackets whose winners were saved without advancing slots.
        sync_playoff_advancement(playoff)

        # Refresh bracket objects so newly advanced teams appear on this response.
        ties = list(
            PlayoffTie.objects.filter(playoff=playoff)
            .select_related("home_team", "away_team")
            .prefetch_related("match_links__match")
        )
        ties_by_round = {}
        for tie in ties:
            matches = get_tie_matches(tie)
            first_leg = get_tie_match(tie, PlayoffMatch.FIRST) or get_tie_match(tie, PlayoffMatch.SINGLE)
            second_leg = get_tie_match(tie, PlayoffMatch.SECOND)
            home_points, away_points = get_tie_points(tie)

            def score_for(match, team):
                if not match or match.status != "finished" or not team:
                    return "—"
                if match.home_team_id == team.id:
                    return match.home_score
                if match.away_team_id == team.id:
                    return match.away_score
                return "—"

            needs_penalties = (
                bool(matches)
                and all(match.status == "finished" for match in matches)
                and home_points == away_points
                and tie.winner_id is None
                and playoff.settings.penalties_on_aggregate_tie
                and not playoff.settings.sporting_advantage_on_tie
            )
            ties_by_round.setdefault(tie.round, []).append(
                {
                    "tie": tie,
                    "first_leg_label": "IDA" if second_leg else "PARTIDO",
                    "has_second_leg": second_leg is not None,
                    "home_first_score": score_for(first_leg, tie.home_team),
                    "away_first_score": score_for(first_leg, tie.away_team),
                    "home_second_score": score_for(second_leg, tie.home_team),
                    "away_second_score": score_for(second_leg, tie.away_team),
                    "matches": matches,
                    "home_points": home_points,
                    "away_points": away_points,
                    "needs_penalties": needs_penalties,
                    "penalties_form": PlayoffPenaltiesForm(),
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
            "is_organizer": getattr(request.user, "role", None) == "ORGANIZER",
            "next_schedulable_round": get_next_schedulable_round(playoff) if playoff else None,
            "next_schedulable_round_label": ROUND_SCHEDULE_LABELS.get(get_next_schedulable_round(playoff)) if playoff else None,
        },
    )


@organizer_required
def schedule_playoff_round_view(request, round_code):
    category = get_request_championship_category(request)
    playoff = Playoff.objects.filter(category=category, is_active=True).select_related("settings").first()
    redirect_url = f"{reverse('playoffs')}?category={category}"
    if not playoff:
        messages.error(request, "No hay un cuadro activo para programar.")
        return redirect(redirect_url)

    ready_round = get_next_schedulable_round(playoff)
    if ready_round != round_code:
        messages.error(request, "La ronda todavía no está lista o ya tiene partidos programados.")
        return redirect(redirect_url)

    round_label = dict(PlayoffTie.ROUND_CHOICES)[round_code]
    if request.method == "POST":
        form = PlayoffRoundScheduleForm(request.POST)
        if form.is_valid():
            try:
                schedule_playoff_round(
                    playoff=playoff,
                    round_code=round_code,
                    match_date=form.cleaned_data["match_date"],
                    match_time=form.cleaned_data["match_time"],
                    court=form.cleaned_data["court"],
                    home_and_away=form.cleaned_data["format"] == PlayoffRoundScheduleForm.HOME_AND_AWAY,
                    second_leg_date=form.cleaned_data["second_leg_date"],
                    second_leg_time=form.cleaned_data["second_leg_time"],
                )
            except ValidationError as error:
                for error_message in error.messages:
                    form.add_error(None, error_message)
            else:
                messages.success(request, f"Jornada de {round_label.lower()} creada correctamente.")
                return redirect(redirect_url)
    else:
        form = PlayoffRoundScheduleForm(
            initial={
                "format": (
                    PlayoffRoundScheduleForm.HOME_AND_AWAY
                    if playoff.settings.final_home_and_away and round_code == PlayoffTie.FINAL
                    else PlayoffRoundScheduleForm.HOME_AND_AWAY
                    if playoff.settings.playoffs_home_and_away
                    else PlayoffRoundScheduleForm.SINGLE
                )
            }
        )

    round_ties = list(playoff.ties.filter(round=round_code).select_related("home_team", "away_team"))
    return render(
        request,
        "playoffs/schedule_round.html",
        {
            "playoff": playoff,
            "round_code": round_code,
            "round_label": round_label,
            "round_schedule_label": ROUND_SCHEDULE_LABELS.get(round_code, round_label.lower()),
            "round_ties": round_ties,
            "form": form,
            "penalties_enabled": playoff.settings.penalties_on_aggregate_tie,
        },
    )


@organizer_required
def record_playoff_penalties_view(request, tie_id):
    if request.method != "POST":
        return redirect(reverse("playoffs"))

    category = get_request_championship_category(request)
    tie = PlayoffTie.objects.select_related("playoff__settings").filter(
        pk=tie_id,
        playoff__category=category,
        playoff__is_active=True,
    ).first()
    redirect_url = f"{reverse('playoffs')}?category={category}"
    if not tie:
        messages.error(request, "No se encontró la llave activa para registrar los penales.")
        return redirect(redirect_url)

    form = PlayoffPenaltiesForm(request.POST)
    matches = get_tie_matches(tie)
    home_points, away_points = get_tie_points(tie)
    if not matches or any(match.status != "finished" for match in matches):
        messages.error(request, "Finaliza todos los partidos de la llave antes de registrar los penales.")
    elif tie.winner_id:
        messages.error(request, "Esta llave ya tiene un equipo clasificado.")
    elif home_points != away_points:
        messages.error(request, "Solo se registran penales cuando la llave queda empatada en puntos.")
    elif not form.is_valid():
        for error in form.non_field_errors():
            messages.error(request, error)
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
    else:
        try:
            resolved_tie = record_penalty_result(
                tie,
                form.cleaned_data["home_penalties"],
                form.cleaned_data["away_penalties"],
            )
        except ValidationError as error:
            for error_message in error.messages:
                messages.error(request, error_message)
        else:
            messages.success(request, f"Penales registrados. Clasifica {resolved_tie.winner.name}.")

    return redirect(redirect_url)


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