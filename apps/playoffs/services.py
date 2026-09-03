"""Business rules for generating and resolving knockout brackets."""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.matches.models import Match
from apps.playoffs.models import LeagueSettings, Playoff, PlayoffTie
from apps.standings.services import build_standings
from apps.teams.models import Team


ROUND_BY_TEAM_COUNT = {
    16: PlayoffTie.ROUND_OF_16,
    8: PlayoffTie.QUARTERFINAL,
    4: PlayoffTie.SEMIFINAL,
    2: PlayoffTie.FINAL,
}
NEXT_ROUND = {
    PlayoffTie.ROUND_OF_16: PlayoffTie.QUARTERFINAL,
    PlayoffTie.QUARTERFINAL: PlayoffTie.SEMIFINAL,
    PlayoffTie.SEMIFINAL: PlayoffTie.FINAL,
}


def get_teams_classified(category):
    """Return the configured qualification limit without creating settings on reads."""
    return LeagueSettings.objects.filter(category=category).values_list("teams_classified", flat=True).first() or 8


def get_league_settings(category):
    """Return the saved category rules, creating the default rules when absent."""
    settings, _ = LeagueSettings.objects.get_or_create(category=category)
    return settings


def generate_playoff(category, match_date, match_time, court=Match.COURT_1, second_leg_date=None, second_leg_time=None):
    """Seed a new active playoff using the current standings for a category."""
    settings = get_league_settings(category)
    settings.full_clean()
    if not settings.playoffs_enabled:
        raise ValidationError("Los playoffs no estan habilitados para esta categoria.")
    if Playoff.objects.filter(category=category, is_active=True).exists():
        raise ValidationError("Ya existe una edicion activa de playoffs para esta categoria.")

    standings = build_standings(category=category, include_adjustments=True)
    if len(standings) < settings.teams_classified:
        raise ValidationError("No hay suficientes equipos clasificados para generar el cuadro.")

    team_by_slug = {
        team.slug: team
        for team in Team.objects.filter(category=category, slug__in=[standing["team_slug"] for standing in standings])
    }
    ranked_teams = [team_by_slug[standing["team_slug"]] for standing in standings[:settings.teams_classified]]
    if len(ranked_teams) != settings.teams_classified:
        raise ValidationError("No se pudieron resolver los equipos clasificados.")

    with transaction.atomic():
        playoff = Playoff.objects.create(category=category, settings=settings)
        initial_round = ROUND_BY_TEAM_COUNT[settings.teams_classified]
        for position in range(1, (settings.teams_classified // 2) + 1):
            home_team = ranked_teams[position - 1]
            away_team = ranked_teams[-position]
            first_leg, second_leg = _create_tie_matches(
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                match_time=match_time,
                court=court,
                home_and_away=settings.playoffs_home_and_away,
                second_leg_date=second_leg_date,
                second_leg_time=second_leg_time,
            )
            PlayoffTie.objects.create(
                playoff=playoff,
                round=initial_round,
                position=position,
                home_team=home_team,
                away_team=away_team,
                first_leg=first_leg,
                second_leg=second_leg,
            )

        _create_pending_rounds(playoff, settings.teams_classified, settings.third_place_match)
    return playoff


def _create_tie_matches(home_team, away_team, match_date, match_time, court, home_and_away, second_leg_date, second_leg_time):
    if not home_and_away:
        return Match.objects.create(
            home_team=home_team,
            away_team=away_team,
            date=match_date,
            time=match_time,
            court=court,
        ), None

    first_leg = Match.objects.create(
        home_team=away_team,
        away_team=home_team,
        date=match_date,
        time=match_time,
        court=court,
    )
    second_leg = Match.objects.create(
        home_team=home_team,
        away_team=away_team,
        date=second_leg_date or match_date,
        time=second_leg_time or match_time,
        court=court,
    )
    return first_leg, second_leg


def _create_pending_rounds(playoff, teams_count, third_place_match):
    current_count = teams_count
    while current_count > 2:
        current_count //= 2
        round_name = ROUND_BY_TEAM_COUNT[current_count]
        for position in range(1, (current_count // 2) + 1):
            PlayoffTie.objects.create(playoff=playoff, round=round_name, position=position)
    if third_place_match and teams_count >= 4:
        PlayoffTie.objects.create(playoff=playoff, round=PlayoffTie.THIRD_PLACE, position=1)


def get_tie_aggregate(tie):
    """Return the regular-time goals accumulated by each seeded team in a tie."""
    home_goals = 0
    away_goals = 0
    for match in (tie.first_leg, tie.second_leg):
        if not match:
            continue
        if match.home_team_id == tie.home_team_id:
            home_goals += match.home_score
            away_goals += match.away_score
        else:
            home_goals += match.away_score
            away_goals += match.home_score
    return home_goals, away_goals


def record_penalty_result(tie, home_penalties, away_penalties):
    """Store a valid penalty result for an otherwise tied, completed series."""
    with transaction.atomic():
        tie = PlayoffTie.objects.select_for_update().select_related("first_leg", "second_leg").get(pk=tie.pk)
        _validate_completed_tie(tie)
        home_goals, away_goals = get_tie_aggregate(tie)
        if home_goals != away_goals:
            raise ValidationError("Los penales solo aplican cuando el marcador global esta empatado.")
        if not tie.playoff.settings.penalties_on_aggregate_tie:
            raise ValidationError("La definicion por penales no esta habilitada para estos playoffs.")
        if home_penalties == away_penalties:
            raise ValidationError("Los penales deben determinar un ganador.")
        tie.home_penalties = home_penalties
        tie.away_penalties = away_penalties
        tie.decided_by_penalties = True
        tie.save(update_fields=["home_penalties", "away_penalties", "decided_by_penalties", "updated_at"])
        return resolve_tie(tie)


def resolve_tie(tie):
    """Determine a completed tie winner and place teams in their next matches."""
    with transaction.atomic():
        tie = PlayoffTie.objects.select_for_update().select_related("playoff__settings", "first_leg", "second_leg").get(pk=tie.pk)
        _validate_completed_tie(tie)
        home_goals, away_goals = get_tie_aggregate(tie)
        if home_goals == away_goals:
            if not tie.decided_by_penalties:
                raise ValidationError("La llave esta empatada y requiere definicion por penales.")
            winner = tie.home_team if tie.home_penalties > tie.away_penalties else tie.away_team
        else:
            winner = tie.home_team if home_goals > away_goals else tie.away_team
        loser = tie.away_team if winner == tie.home_team else tie.home_team

        tie.winner = winner
        tie.loser = loser
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
    next_round = NEXT_ROUND.get(tie.round)
    if next_round:
        next_tie = PlayoffTie.objects.select_for_update().get(
            playoff=tie.playoff,
            round=next_round,
            position=(tie.position + 1) // 2,
        )
        team_field = "home_team" if tie.position % 2 else "away_team"
        setattr(next_tie, team_field, tie.winner)
        next_tie.save(update_fields=[team_field, "updated_at"])

    if tie.round == PlayoffTie.SEMIFINAL and tie.playoff.settings.third_place_match:
        third_place = PlayoffTie.objects.select_for_update().get(
            playoff=tie.playoff,
            round=PlayoffTie.THIRD_PLACE,
            position=1,
        )
        team_field = "home_team" if tie.position == 1 else "away_team"
        setattr(third_place, team_field, tie.loser)
        third_place.save(update_fields=[team_field, "updated_at"])