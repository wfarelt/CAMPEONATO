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
SCHEDULABLE_ROUNDS = [PlayoffTie.ROUND_OF_16, PlayoffTie.QUARTERFINAL, PlayoffTie.SEMIFINAL, PlayoffTie.FINAL]


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
            ties_in_round = sum(1 for key in ties if key[0] == round_name)
            next_position, next_slot = _bracket_destination(position, ties_in_round)
            tie.next_tie = ties[(next_round, next_position)]
            tie.next_slot = next_slot
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


def _bracket_destination(position, ties_in_round):
    """Pair outer and inner bracket ties: 1 vs N, 2 vs N-1, and so on."""
    return min(position, ties_in_round + 1 - position), "home" if position <= ties_in_round // 2 else "away"


def get_next_schedulable_round(playoff):
    """Return the earliest populated round whose fixtures have not been created."""
    for round_code in SCHEDULABLE_ROUNDS:
        ties = list(playoff.ties.filter(round=round_code).prefetch_related("match_links"))
        if not ties:
            continue
        if any(tie.home_team_id is None or tie.away_team_id is None for tie in ties):
            return None
        tie_has_matches = [bool(tie.match_links.all()) for tie in ties]
        if not any(tie_has_matches):
            return round_code
        if not all(tie_has_matches):
            return None
    return None


def sync_playoff_advancement(playoff):
    """Resolve finished ties and backfill the next-round slots for existing brackets."""
    for round_code in SCHEDULABLE_ROUNDS:
        stage_ties = list(
            playoff.ties.filter(round=round_code)
            .select_related("home_team", "away_team", "winner", "playoff__settings")
            .order_by("position")
        )
        if not stage_ties:
            continue
        for tie_index, tie in enumerate(stage_ties):
            matches = get_tie_matches(tie)
            if tie.winner_id is None and matches and all(match.status == "finished" for match in matches):
                home_points, away_points = get_tie_points(tie)
                if home_points != away_points or tie.playoff.settings.sporting_advantage_on_tie or tie.decided_by_penalties:
                    tie = resolve_tie(tie)
                    stage_ties[tie_index] = tie

        next_round = NEXT_ROUND.get(round_code)
        if not next_round:
            continue

        next_ties = list(playoff.ties.filter(round=next_round).order_by("position"))
        if not next_ties:
            continue

        linked_matches = [
            link.match
            for next_tie in next_ties
            for link in next_tie.match_links.select_related("match")
        ]
        # Never rewrite a round once one of its games has been completed.
        if any(match.status != "scheduled" for match in linked_matches):
            continue

        # Existing brackets may have winners routed with the old sequential pairing
        # (1 vs 2, 3 vs 4). Rebuild empty next-round slots using bracket pairing
        # (1 vs 4, 2 vs 3) before the organizer schedules fixtures.
        for next_tie in next_ties:
            next_tie.home_team = None
            next_tie.away_team = None
            next_tie.save(update_fields=["home_team", "away_team", "updated_at"])

        tie_count = len(stage_ties)
        for tie in stage_ties:
            if not tie.winner_id:
                continue
            next_position, slot = _bracket_destination(tie.position, tie_count)
            next_tie = next((item for item in next_ties if item.position == next_position), None)
            if not next_tie:
                continue
            slot = f"{slot}_team"
            setattr(next_tie, slot, tie.winner)
            next_tie.save(update_fields=[slot, "updated_at"])

        # If this round was already scheduled, update its unplayed fixtures to match
        # the corrected bracket pairings while preserving dates, courts and matchdays.
        for next_tie in next_ties:
            for link in next_tie.match_links.select_related("match"):
                match = link.match
                if link.leg == PlayoffMatch.FIRST:
                    match.home_team = next_tie.away_team
                    match.away_team = next_tie.home_team
                else:
                    match.home_team = next_tie.home_team
                    match.away_team = next_tie.away_team
                match.save(update_fields=["home_team", "away_team"])


def schedule_playoff_round(
    playoff,
    round_code,
    match_date,
    match_time,
    court=Match.COURT_1,
    home_and_away=False,
    second_leg_date=None,
    second_leg_time=None,
):
    """Create matchday fixtures for the next fully qualified playoff round."""
    if round_code not in SCHEDULABLE_ROUNDS or get_next_schedulable_round(playoff) != round_code:
        raise ValidationError("Esta ronda todavía no está lista para programarse.")
    if home_and_away and (not second_leg_date or not second_leg_time):
        raise ValidationError("Indica fecha y hora para el partido de vuelta.")
    if home_and_away and second_leg_date <= match_date:
        raise ValidationError("La fecha de vuelta debe ser posterior a la fecha de ida.")

    with transaction.atomic():
        ties = list(playoff.ties.filter(round=round_code).select_related("home_team", "away_team"))
        for tie in ties:
            _create_tie_matches(
                tie,
                playoff.category,
                tie.home_team,
                tie.away_team,
                match_date,
                match_time,
                court,
                home_and_away,
                second_leg_date,
                second_leg_time,
            )
    return ties


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
    first_match = get_tie_match(tie, PlayoffMatch.FIRST) or get_tie_match(tie, PlayoffMatch.SINGLE)
    second_match = get_tie_match(tie, PlayoffMatch.SECOND)
    return [match for match in (first_match, second_match) if match]


def get_tie_match(tie, leg):
    """Resolve a leg only when its match actually contains the teams in this tie."""
    linked_matches = {link.leg: link.match for link in tie.match_links.all()}
    match = linked_matches.get(leg)
    if match and _match_has_tie_teams(match, tie):
        return match
    if not tie.home_team_id or not tie.away_team_id:
        return None

    # Team assignments can be edited after the bracket fixtures are generated.
    # In that case, another tie's leg link may now own the fixture for this pairing.
    for link in PlayoffMatch.objects.filter(
        tie__playoff_id=tie.playoff_id,
        tie__round=tie.round,
        leg=leg,
    ).exclude(tie_id=tie.pk).select_related("match"):
        if _match_has_tie_teams(link.match, tie):
            return link.match
    return None


def _match_has_tie_teams(match, tie):
    return {match.home_team_id, match.away_team_id} == {tie.home_team_id, tie.away_team_id}


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


def get_tie_points(tie):
    """Return the points earned by each team across completed matches in a tie."""
    home_points = away_points = 0
    for match in get_tie_matches(tie):
        if match.status != "finished":
            continue
        if match.home_score == match.away_score:
            home_points += 1
            away_points += 1
        elif (match.home_team_id == tie.home_team_id and match.home_score > match.away_score) or (
            match.away_team_id == tie.home_team_id and match.away_score > match.home_score
        ):
            home_points += 3
        else:
            away_points += 3
    return home_points, away_points


def record_penalty_result(tie, home_penalties, away_penalties):
    with transaction.atomic():
        tie = PlayoffTie.objects.select_for_update().select_related("playoff__settings").get(pk=tie.pk)
        _validate_completed_tie(tie)
        if get_tie_points(tie)[0] != get_tie_points(tie)[1]:
            raise ValidationError("Los penales solo aplican cuando los equipos empatan en puntos.")
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
        home_points, away_points = get_tie_points(tie)
        if home_points == away_points:
            if tie.playoff.settings.sporting_advantage_on_tie:
                winner = tie.home_team
            elif tie.decided_by_penalties:
                winner = tie.home_team if tie.home_penalties > tie.away_penalties else tie.away_team
            else:
                raise ValidationError("La llave esta empatada en puntos y requiere definicion por penales.")
        else:
            winner = tie.home_team if home_points > away_points else tie.away_team
        tie.winner = winner
        tie.loser = tie.away_team if winner == tie.home_team else tie.home_team
        tie.save(update_fields=["winner", "loser", "updated_at"])
        _advance_tie(tie)
    return tie


def _validate_completed_tie(tie):
    matches = get_tie_matches(tie)
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