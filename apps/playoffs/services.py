"""Services for category-based knockout playoffs."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.matches.models import Match
from apps.playoffs.models import LeagueSettings, Playoff, PlayoffMatch, PlayoffTie
from apps.standings.services import build_standings
from apps.teams.models import Team
from apps.tournaments.models import MatchDay


ROUND_BY_TEAM_COUNT = {16: PlayoffTie.ROUND_OF_16, 8: PlayoffTie.QUARTERFINAL, 4: PlayoffTie.SEMIFINAL, 2: PlayoffTie.FINAL}
NEXT_ROUND = {PlayoffTie.ROUND_OF_16: PlayoffTie.QUARTERFINAL, PlayoffTie.QUARTERFINAL: PlayoffTie.SEMIFINAL, PlayoffTie.SEMIFINAL: PlayoffTie.FINAL}


def get_teams_classified(category):
    return LeagueSettings.objects.filter(category=category).values_list("teams_classified", flat=True).first() or 8


def get_league_settings(category):
    settings, _ = LeagueSettings.objects.get_or_create(category=category)
    return settings


def generate_playoff(category, match_date, match_time, court=Match.COURT_1, second_leg_date=None, second_leg_time=None):
    settings = get_league_settings(category)
    settings.full_clean()
    if not settings.playoffs_enabled:
        raise ValidationError("Los playoffs no estan habilitados para esta categoria.")
    if Playoff.objects.filter(category=category, is_active=True).exists():
        raise ValidationError("Ya existe un cuadro activo de playoffs para esta categoria.")

    standings = build_standings(category=category, include_adjustments=True)
    if len(standings) < settings.teams_classified:
        raise ValidationError("No hay suficientes equipos clasificados para generar el cuadro.")
    slugs = [standing["team_slug"] for standing in standings[:settings.teams_classified]]
    teams = {team.slug: team for team in Team.objects.filter(category=category, slug__in=slugs)}
    ranked_teams = [teams[slug] for slug in slugs if slug in teams]
    if len(ranked_teams) != settings.teams_classified:
        raise ValidationError("No se pudieron resolver los equipos clasificados.")

    with transaction.atomic():
        playoff = Playoff.objects.create(category=category, settings=settings)
        ties = _create_bracket(playoff, settings.teams_classified, settings.third_place_match)
        initial_round = ROUND_BY_TEAM_COUNT[settings.teams_classified]
        for position in range(1, settings.teams_classified // 2 + 1):
            tie = ties[(initial_round, position)]
            home_team, away_team = ranked_teams[position - 1], ranked_teams[-position]
            tie.home_team, tie.away_team = home_team, away_team
            tie.save(update_fields=["home_team", "away_team", "updated_at"])
            _create_tie_matches(tie, category, home_team, away_team, match_date, match_time, court, settings.playoffs_home_and_away, second_leg_date, second_leg_time)
    return playoff


def _create_bracket(playoff, teams_count, third_place_match):
    ties = {}
    current_count = teams_count
    while current_count >= 2:
        round_name = ROUND_BY_TEAM_COUNT[current_count]
        for position in range(1, current_count // 2 + 1):
            ties[(round_name, position)] = PlayoffTie.objects.create(playoff=playoff, round=round_name, position=position)
        current_count //= 2

    for (round_name, position), tie in ties.items():
        next_round = NEXT_ROUND.get(round_name)
        if next_round:
            tie.next_tie = ties[(next_round, (position + 1) // 2)]
            tie.next_slot = "home" if position % 2 else "away"
            tie.save(update_fields=["next_tie", "next_slot", "updated_at"])

    if third_place_match and teams_count >= 4:
        third_place = PlayoffTie.objects.create(playoff=playoff, round=PlayoffTie.THIRD_PLACE, position=1)
        for position in (1, 2):
            tie = ties[(PlayoffTie.SEMIFINAL, position)]
            tie.next_tie = third_place
            tie.next_slot = "home" if position == 1 else "away"
            tie.save(update_fields=["next_tie", "next_slot", "updated_at"])
        ties[(PlayoffTie.THIRD_PLACE, 1)] = third_place
    return ties


def _create_tie_matches(tie, category, home_team, away_team, match_date, match_time, court, home_and_away, second_leg_date, second_leg_time):
    first_day = _get_match_day(category, match_date, tie.get_round_display() + (" (ida)" if home_and_away else ""), is_visible=True)
    if not home_and_away:
        match = Match.objects.create(home_team=home_team, away_team=away_team, match_day=first_day, date=match_date, time=match_time, court=court)
        PlayoffMatch.objects.create(tie=tie, match=match, leg=PlayoffMatch.SINGLE)
        return

    second_date = second_leg_date or match_date + timedelta(days=1)
    second_day = _get_match_day(category, second_date, tie.get_round_display() + " (vuelta)", is_visible=False)
    first = Match.objects.create(home_team=away_team, away_team=home_team, match_day=first_day, date=match_date, time=match_time, court=court)
    second = Match.objects.create(home_team=home_team, away_team=away_team, match_day=second_day, date=second_date, time=second_leg_time or match_time, court=court)
    PlayoffMatch.objects.bulk_create([PlayoffMatch(tie=tie, match=first, leg=PlayoffMatch.FIRST), PlayoffMatch(tie=tie, match=second, leg=PlayoffMatch.SECOND)])


def _get_match_day(category, date, description, is_visible=True):
    match_day, created = MatchDay.objects.get_or_create(
        category=category,
        date=date,
        defaults={"description": description, "is_visible": is_visible},
    )
    if not created and "(vuelta)" in description and match_day.description == description and match_day.is_visible:
        match_day.is_visible = is_visible
        match_day.save(update_fields=["is_visible", "updated_at"])
    if not match_day.description:
        match_day.description = description
        match_day.is_visible = is_visible
        match_day.save(update_fields=["description", "is_visible", "slug", "updated_at"])
    return match_day


def get_tie_matches(tie):
    return [link.match for link in tie.match_links.select_related("match").order_by("id")]


def get_tie_aggregate(tie):
    home_goals = away_goals = 0
    for match in get_tie_matches(tie):
        if match.home_team_id == tie.home_team_id:
            home_goals += match.home_score
            away_goals += match.away_score
        else:
            home_goals += match.away_score
            away_goals += match.home_score
    return home_goals, away_goals


def record_penalty_result(tie, home_penalties, away_penalties):
    with transaction.atomic():
        tie = PlayoffTie.objects.select_for_update().select_related("playoff__settings").get(pk=tie.pk)
        _validate_completed_tie(tie)
        if get_tie_aggregate(tie)[0] != get_tie_aggregate(tie)[1]:
            raise ValidationError("Los penales solo aplican cuando el marcador global esta empatado.")
        if not tie.playoff.settings.penalties_on_aggregate_tie or home_penalties == away_penalties:
            raise ValidationError("El resultado de penales no es valido para estos playoffs.")
        tie.home_penalties, tie.away_penalties = home_penalties, away_penalties
        tie.decided_by_penalties = True
        tie.save(update_fields=["home_penalties", "away_penalties", "decided_by_penalties", "updated_at"])
        return resolve_tie(tie)


def resolve_tie(tie):
    with transaction.atomic():
        tie = PlayoffTie.objects.select_for_update().select_related("playoff__settings", "next_tie").get(pk=tie.pk)
        _validate_completed_tie(tie)
        home_goals, away_goals = get_tie_aggregate(tie)
        if home_goals == away_goals:
            if tie.playoff.settings.sporting_advantage_on_tie:
                winner = tie.home_team
            elif tie.decided_by_penalties:
                winner = tie.home_team if tie.home_penalties > tie.away_penalties else tie.away_team
            else:
                raise ValidationError("La llave esta empatada y requiere definicion.")
        else:
            winner = tie.home_team if home_goals > away_goals else tie.away_team
        tie.winner = winner
        tie.loser = tie.away_team if winner == tie.home_team else tie.home_team
        tie.save(update_fields=["winner", "loser", "updated_at"])
        _advance_tie(tie)
    return tie


def _validate_completed_tie(tie):
    matches = [match for match in (tie.first_leg, tie.second_leg) if match]
    if not tie.home_team_id or not tie.away_team_id or not matches:
        raise ValidationError("La llave debe tener equipos y partidos asignados.")
    if any(match.status != "finished" for match in matches):
        raise ValidationError("Todos los partidos de la llave deben estar finalizados.")


def _advance_tie(tie):
    if not tie.next_tie or not tie.winner:
        return
    next_tie = PlayoffTie.objects.select_for_update().get(pk=tie.next_tie_id)
    field = "home_team" if tie.next_slot == "home" else "away_team"
    setattr(next_tie, field, tie.winner)
    next_tie.save(update_fields=[field, "updated_at"])