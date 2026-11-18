from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.core.categories import get_request_championship_category, get_request_tournament
from apps.playoffs.forms import PlayoffGenerationForm, PlayoffPenaltiesForm, PlayoffRoundScheduleForm, PlayoffSettingsForm
from apps.playoffs.models import LeagueSettings, Playoff, PlayoffMatch, PlayoffTie
from apps.playoffs.services import (
    generate_playoff,
    get_tie_aggregate,
    get_tie_match,
    get_tie_matches,
    get_next_schedulable_round,
    has_conflicting_downstream_slot,
    calculate_tie_winner,
    confirm_tie_result_change,
    has_played_downstream_match,
    get_league_settings,
    record_penalty_result,
    schedule_playoff_round,
    sync_playoff_advancement,
)
from apps.users.permissions import can_manage_tournament, organizer_required

ROUND_SCHEDULE_LABELS = {
    PlayoffTie.ROUND_OF_16: "octavos de final",
    PlayoffTie.QUARTERFINAL: "cuartos de final",
    PlayoffTie.SEMIFINAL: "semifinales",
    PlayoffTie.FINAL: "final",
}


@login_required
@organizer_required
def playoff_settings_view(request):
    category = get_request_championship_category(request)
    tournament = get_request_tournament(request, category)
    if tournament is None or not can_manage_tournament(request.user, tournament):
        return HttpResponseForbidden("Selecciona un campeonato que tengas permiso para administrar.")

    settings = get_league_settings(category, tournament=tournament)
    settings_locked = Playoff.objects.filter(tournament=tournament, is_active=True).exists()
    if request.method == "POST" and settings_locked:
        messages.error(request, "No se puede cambiar la configuración mientras haya un cuadro activo.")
        return redirect(f"{reverse('playoffs')}?category={category}&tournament={tournament.pk}")

    form = PlayoffSettingsForm(request.POST or None, instance=settings)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La configuración de playoffs se guardó para esta temporada.")
        return redirect(f"{reverse('playoffs')}?category={category}&tournament={tournament.pk}")

    return render(
        request,
        "playoffs/settings.html",
        {
            "form": form,
            "tournament": tournament,
            "settings_locked": settings_locked,
        },
    )


def playoffs_view(request):
    category = get_request_championship_category(request)
    tournament = get_request_tournament(request, category)
    settings = LeagueSettings.objects.filter(category=category, tournament=tournament).first()
    if settings is None and tournament is not None:
        settings = LeagueSettings.objects.filter(category=category, tournament__isnull=True).first()
    if settings is None:
        settings = LeagueSettings(category=category, tournament=tournament)
    playoff_query = Playoff.objects.filter(category=category, is_active=True)
    if tournament is not None:
        playoff_query = playoff_query.filter(tournament=tournament)
    else:
        playoff_query = playoff_query.filter(tournament__isnull=True)
    playoff = playoff_query.select_related("settings", "tournament").prefetch_related(
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
            home_goals, away_goals = get_tie_aggregate(tie)

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
                and home_goals == away_goals
                and tie.winner_id is None
                and playoff.settings.penalties_on_aggregate_tie
                and not playoff.settings.sporting_advantage_on_tie
            )
            calculated_winner = calculate_tie_winner(tie)
            winner_changed = bool(
                tie.winner_id
                and (calculated_winner is None or calculated_winner.pk != tie.winner_id)
            )
            winner_changed = winner_changed or has_conflicting_downstream_slot(tie, calculated_winner)
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
                    "home_aggregate": home_goals,
                    "away_aggregate": away_goals,
                    "needs_penalties": needs_penalties,
                    "winner_changed": winner_changed,
                    "downstream_locked": has_played_downstream_match(tie) if winner_changed else False,
                    "calculated_winner": calculated_winner,
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
            "selected_tournament": tournament,
            "rounds": rounds,
            "generation_form": PlayoffGenerationForm(),
            "is_organizer": (
                getattr(request.user, "role", None) == "ORGANIZER"
                and (tournament is None or can_manage_tournament(request.user, tournament))
            ),
            "next_schedulable_round": get_next_schedulable_round(playoff) if playoff else None,
            "next_schedulable_round_label": ROUND_SCHEDULE_LABELS.get(get_next_schedulable_round(playoff)) if playoff else None,
        },
    )


@organizer_required
def confirm_playoff_result_change_view(request, tie_id):
    if request.method != "POST":
        return redirect(reverse("playoffs"))

    category = get_request_championship_category(request)
    tournament = get_request_tournament(request, category)
    tie = PlayoffTie.objects.select_related("playoff__settings", "playoff__tournament").filter(
        pk=tie_id,
        playoff__category=category,
        playoff__is_active=True,
    ).first()
    redirect_url = f"{reverse('playoffs')}?category={category}"
    if tournament is not None:
        redirect_url += f"&tournament={tournament.pk}"
    if tie and tie.playoff.tournament_id != (tournament.pk if tournament else None):
        tie = None
    if tie and tie.playoff.tournament_id and not can_manage_tournament(request.user, tie.playoff.tournament):
        return HttpResponseForbidden("No tienes permisos para administrar esta temporada.")
    if not tie:
        messages.error(request, "No se encontró la llave para revisar el cambio de resultado.")
        return redirect(redirect_url)

    try:
        updated_tie = confirm_tie_result_change(tie)
    except ValidationError as error:
        for error_message in error.messages:
            messages.error(request, error_message)
    else:
        if updated_tie.winner:
            messages.success(request, f"Cuadro actualizado. Clasifica {updated_tie.winner.name}.")
        else:
            messages.warning(request, "La clasificación anterior fue invalidada. Define la llave según el reglamento.")
    return redirect(redirect_url)


@organizer_required
def schedule_playoff_round_view(request, round_code):
    category = get_request_championship_category(request)
    tournament = get_request_tournament(request, category)
    if tournament is not None and not can_manage_tournament(request.user, tournament):
        return HttpResponseForbidden("No tienes permisos para administrar esta temporada.")
    playoff_query = Playoff.objects.filter(category=category, is_active=True)
    playoff_query = playoff_query.filter(tournament=tournament) if tournament else playoff_query.filter(tournament__isnull=True)
    playoff = playoff_query.select_related("settings", "tournament").first()
    redirect_url = f"{reverse('playoffs')}?category={category}"
    if tournament:
        redirect_url += f"&tournament={tournament.pk}"
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
    tournament = get_request_tournament(request, category)
    tie = PlayoffTie.objects.select_related("playoff__settings").filter(
        pk=tie_id,
        playoff__category=category,
        playoff__is_active=True,
    ).first()
    redirect_url = f"{reverse('playoffs')}?category={category}"
    if tournament:
        redirect_url += f"&tournament={tournament.pk}"
    if tie and tie.playoff.tournament_id != (tournament.pk if tournament else None):
        tie = None
    if tie and tie.playoff.tournament_id and not can_manage_tournament(request.user, tie.playoff.tournament):
        return HttpResponseForbidden("No tienes permisos para administrar esta temporada.")
    if not tie:
        messages.error(request, "No se encontró la llave activa para registrar los penales.")
        return redirect(redirect_url)

    form = PlayoffPenaltiesForm(request.POST)
    matches = get_tie_matches(tie)
    home_goals, away_goals = get_tie_aggregate(tie)
    if not matches or any(match.status != "finished" for match in matches):
        messages.error(request, "Finaliza todos los partidos de la llave antes de registrar los penales.")
    elif tie.winner_id:
        messages.error(request, "Esta llave ya tiene un equipo clasificado.")
    elif home_goals != away_goals:
        messages.error(request, "Solo se registran penales cuando el marcador global de la llave está empatado.")
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
    tournament = get_request_tournament(request, category)
    redirect_url = f"{reverse('playoffs')}?category={category}"
    if tournament:
        redirect_url += f"&tournament={tournament.pk}"
        if not can_manage_tournament(request.user, tournament):
            return HttpResponseForbidden("No tienes permisos para administrar esta temporada.")
    form = PlayoffGenerationForm(request.POST)
    if form.is_valid():
        try:
            generate_playoff(category=category, tournament=tournament, **form.cleaned_data)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            messages.success(request, "El cuadro de playoffs fue generado.")
    else:
        messages.error(request, "Revisa la fecha, hora y cancha para generar el cuadro.")

    return redirect(redirect_url)