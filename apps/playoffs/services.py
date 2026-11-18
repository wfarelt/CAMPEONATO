"""Services for category-based knockout playoffs."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.matches.models import Match
from apps.playoffs.models import LeagueSettings, Playoff, PlayoffMatch, PlayoffTie
from apps.standings.services import build_standings
from apps.teams.models import Team
from apps.tournaments.models import MatchDay


ROUND_BY_TEAM_COUNT = {
    64: PlayoffTie.ROUND_OF_64,
    32: PlayoffTie.ROUND_OF_32,
    16: PlayoffTie.ROUND_OF_16,
    8: PlayoffTie.QUARTERFINAL,
    4: PlayoffTie.SEMIFINAL,
    2: PlayoffTie.FINAL,
}
NEXT_ROUND = {
    PlayoffTie.ROUND_OF_64: PlayoffTie.ROUND_OF_32,
    PlayoffTie.ROUND_OF_32: PlayoffTie.ROUND_OF_16,
    PlayoffTie.ROUND_OF_16: PlayoffTie.QUARTERFINAL,
    PlayoffTie.QUARTERFINAL: PlayoffTie.SEMIFINAL,
    PlayoffTie.SEMIFINAL: PlayoffTie.FINAL,
}
SCHEDULABLE_ROUNDS = [
    PlayoffTie.ROUND_OF_64,
    PlayoffTie.ROUND_OF_32,
    PlayoffTie.ROUND_OF_16,
    PlayoffTie.QUARTERFINAL,
    PlayoffTie.SEMIFINAL,
    PlayoffTie.FINAL,
]


def get_teams_classified(category, tournament=None):
    settings_query = LeagueSettings.objects.filter(category=category, tournament=tournament)
    settings = settings_query.first()
    if settings is None and tournament is not None:
        settings = LeagueSettings.objects.filter(category=category, tournament__isnull=True).first()
    return settings.teams_classified if settings else 8


def get_league_settings(category, tournament=None):
    if tournament is None:
        settings, _ = LeagueSettings.objects.get_or_create(category=category, tournament__isnull=True)
        return settings
    if tournament.category != category:
        raise ValidationError("El campeonato seleccionado no pertenece a esta categoría.")

    legacy = LeagueSettings.objects.filter(category=category, tournament__isnull=True).first()
    defaults = {
        "category": category,
        "teams_classified": legacy.teams_classified if legacy else 8,
        "playoffs_enabled": legacy.playoffs_enabled if legacy else False,
        "third_place_match": legacy.third_place_match if legacy else True,
        "playoffs_home_and_away": legacy.playoffs_home_and_away if legacy else False,
        "final_home_and_away": legacy.final_home_and_away if legacy else False,
        "penalties_on_aggregate_tie": legacy.penalties_on_aggregate_tie if legacy else True,
        "sporting_advantage_on_tie": legacy.sporting_advantage_on_tie if legacy else False,
        "replay_on_aggregate_tie": legacy.replay_on_aggregate_tie if legacy else False,
    }
    settings, _ = LeagueSettings.objects.get_or_create(tournament=tournament, defaults=defaults)
    return settings


def generate_playoff(category, match_date, match_time, court=Match.COURT_1, second_leg_date=None, second_leg_time=None, tournament=None):
    settings = get_league_settings(category, tournament=tournament)
    settings.full_clean()
    if tournament is not None and tournament.category != category:
        raise ValidationError("El campeonato seleccionado no pertenece a esta categoría.")
    if not settings.playoffs_enabled:
        raise ValidationError("Los playoffs no estan habilitados para esta categoria.")
    active_playoffs = Playoff.objects.filter(category=category, is_active=True)
    pending_matches = Match.objects.filter(
        home_team__category=category,
        away_team__category=category,
        status="scheduled",
        playoff_link__isnull=True,
    )
    if tournament is not None:
        active_playoffs = active_playoffs.filter(tournament=tournament)
        pending_matches = pending_matches.filter(match_day__tournament=tournament)
    else:
        active_playoffs = active_playoffs.filter(tournament__isnull=True)
        pending_matches = pending_matches.filter(match_day__tournament__isnull=True)
    if pending_matches.exists():
        raise ValidationError("No se pueden generar los playoffs: aún hay partidos de la fase regular pendientes.")
    if active_playoffs.exists():
        raise ValidationError("Ya existe un cuadro activo de playoffs para esta categoria.")

    standings = build_standings(category=category, include_adjustments=True, tournament=tournament)
    if len(standings) < settings.teams_classified:
        raise ValidationError("No hay suficientes equipos clasificados para generar el cuadro.")
    slugs = [standing["team_slug"] for standing in standings[:settings.teams_classified]]
    teams_query = Team.objects.filter(category=category, slug__in=slugs)
    if tournament is not None:
        teams_query = teams_query.filter(tournament_memberships__tournament=tournament)
    teams = {team.slug: team for team in teams_query}
    ranked_teams = [teams[slug] for slug in slugs if slug in teams]
    if len(ranked_teams) != settings.teams_classified:
        raise ValidationError("No se pudieron resolver los equipos clasificados.")

    with transaction.atomic():
        playoff = Playoff.objects.create(category=category, settings=settings, tournament=tournament)
        bracket_size = 1 << (settings.teams_classified - 1).bit_length()
        ties = _create_bracket(
            playoff,
            bracket_size,
            settings.third_place_match,
            participants_count=settings.teams_classified,
        )
        initial_round = ROUND_BY_TEAM_COUNT[bracket_size]
        for position in range(1, bracket_size // 2 + 1):
            tie = ties[(initial_round, position)]
            home_seed = position
            away_seed = bracket_size - position + 1
            home_team = ranked_teams[home_seed - 1]
            if away_seed > len(ranked_teams):
                tie.home_team = home_team
                tie.winner = home_team
                tie.is_bye = True
                tie.save(update_fields=["home_team", "winner", "is_bye", "updated_at"])
                _advance_tie(tie)
                continue

            away_team = ranked_teams[away_seed - 1]
            tie.home_team, tie.away_team = home_team, away_team
            tie.save(update_fields=["home_team", "away_team", "updated_at"])
            _create_tie_matches(
                tie,
                category,
                home_team,
                away_team,
                match_date,
                match_time,
                court,
                settings.playoffs_home_and_away,
                second_leg_date,
                second_leg_time,
                tournament=tournament,
            )
    return playoff


def _create_bracket(playoff, bracket_size, third_place_match, participants_count=None):
    ties = {}
    current_count = bracket_size
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

    if third_place_match and (participants_count or bracket_size) >= 4:
        third_place = PlayoffTie.objects.create(playoff=playoff, round=PlayoffTie.THIRD_PLACE, position=1)
        ties[(PlayoffTie.THIRD_PLACE, 1)] = third_place
    return ties


def _create_tie_matches(tie, category, home_team, away_team, match_date, match_time, court, home_and_away, second_leg_date, second_leg_time, tournament=None):
    first_day = _get_match_day(category, match_date, tie.get_round_display() + (" (ida)" if home_and_away else ""), is_visible=True, tournament=tournament)
    if not home_and_away:
        match = Match.objects.create(home_team=home_team, away_team=away_team, match_day=first_day, date=match_date, time=match_time, court=court)
        PlayoffMatch.objects.create(tie=tie, match=match, leg=PlayoffMatch.SINGLE)
        return

    second_date = second_leg_date or match_date + timedelta(days=1)
    second_day = _get_match_day(category, second_date, tie.get_round_display() + " (vuelta)", is_visible=False, tournament=tournament)
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
        if any(tie.home_team_id is None or (tie.away_team_id is None and not tie.is_bye) for tie in ties):
            return None
        playable_ties = [tie for tie in ties if not tie.is_bye]
        if not playable_ties:
            continue
        tie_has_matches = [bool(tie.match_links.all()) for tie in playable_ties]
        if not any(tie_has_matches):
            return round_code
        if not all(tie_has_matches):
            return None
    return None


def sync_playoff_advancement(playoff):
    """Resolve finished ties and backfill the next-round slots for existing brackets."""
    blocked_rounds = set()
    for round_code in SCHEDULABLE_ROUNDS:
        if round_code in blocked_rounds:
            continue
        stage_ties = list(
            playoff.ties.filter(round=round_code)
            .select_related("home_team", "away_team", "winner", "playoff__settings")
            .order_by("position")
        )
        if not stage_ties:
            continue
        for tie_index, tie in enumerate(stage_ties):
            matches = get_tie_matches(tie)
            if tie.winner_id and matches:
                calculated_winner = calculate_tie_winner(tie)
                if calculated_winner is None or calculated_winner.pk != tie.winner_id:
                    blocked_rounds.update(_downstream_round_codes(round_code))
                    continue
            if tie.winner_id is None and matches and all(match.status == "finished" for match in matches):
                home_goals, away_goals = get_tie_aggregate(tie)
                if home_goals != away_goals or tie.playoff.settings.sporting_advantage_on_tie or tie.decided_by_penalties:
                    try:
                        tie = resolve_tie(tie)
                        stage_ties[tie_index] = tie
                    except ValidationError:
                        blocked_rounds.update(_downstream_round_codes(round_code))
                        continue

        next_round = NEXT_ROUND.get(round_code)
        if not next_round or next_round in blocked_rounds:
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

    _sync_third_place(playoff)


def _sync_third_place(playoff):
    third_place = playoff.ties.filter(round=PlayoffTie.THIRD_PLACE).first()
    semifinal_ties = list(
        playoff.ties.filter(round=PlayoffTie.SEMIFINAL).order_by("position")
    )
    if not third_place or len(semifinal_ties) != 2:
        return

    matches = [link.match for link in third_place.match_links.select_related("match")]
    if any(match.status != "scheduled" for match in matches):
        return

    third_place.home_team = semifinal_ties[0].loser
    third_place.away_team = semifinal_ties[1].loser
    third_place.save(update_fields=["home_team", "away_team", "updated_at"])
    for link in third_place.match_links.select_related("match"):
        match = link.match
        if link.leg == PlayoffMatch.FIRST:
            match.home_team = third_place.away_team
            match.away_team = third_place.home_team
        else:
            match.home_team = third_place.home_team
            match.away_team = third_place.away_team
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
                tournament=playoff.tournament,
            )
    return ties


def _get_match_day(category, date, description, is_visible=True, tournament=None):
    match_day, created = MatchDay.objects.get_or_create(
        category=category,
        date=date,
        tournament=tournament,
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
    """Return completed aggregate goals oriented to the tie's home and away teams."""
    home_goals = away_goals = 0
    for match in get_tie_matches(tie):
        if match.status != "finished":
            continue
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
        if get_tie_aggregate(tie)[0] != get_tie_aggregate(tie)[1]:
            raise ValidationError("Los penales solo aplican cuando el marcador global está empatado.")
        if not tie.playoff.settings.penalties_on_aggregate_tie or home_penalties == away_penalties:
            raise ValidationError("El resultado de penales no es valido para estos playoffs.")
        tie.home_penalties, tie.away_penalties = home_penalties, away_penalties
        tie.decided_by_penalties = True
        tie.save(update_fields=["home_penalties", "away_penalties", "decided_by_penalties", "updated_at"])
        return resolve_tie(tie)


def resolve_tie(tie):
    return _resolve_tie(tie, confirm_result_change=False)


def confirm_tie_result_change(tie):
    """Apply a changed winner only after explicit organizer confirmation."""
    return _resolve_tie(tie, confirm_result_change=True)


def calculate_tie_winner(tie):
    """Calculate the current winner from match scores without mutating the bracket."""
    matches = get_tie_matches(tie)
    if not tie.home_team_id or not tie.away_team_id or not matches:
        return None
    if any(match.status != "finished" for match in matches):
        return None

    home_goals, away_goals = get_tie_aggregate(tie)
    if home_goals == away_goals:
        if tie.playoff.settings.sporting_advantage_on_tie:
            return tie.home_team
        if tie.decided_by_penalties and tie.home_penalties is not None and tie.away_penalties is not None:
            return tie.home_team if tie.home_penalties > tie.away_penalties else tie.away_team
        return None
    return tie.home_team if home_goals > away_goals else tie.away_team


def _resolve_tie(tie, *, confirm_result_change):
    with transaction.atomic():
        tie = PlayoffTie.objects.select_for_update().select_related("playoff__settings", "next_tie").get(pk=tie.pk)
        _validate_completed_tie(tie)
        previous_winner_id = tie.winner_id
        winner = calculate_tie_winner(tie)
        if winner is None and previous_winner_id is None:
            raise ValidationError("La llave está empatada en el marcador global y requiere definición por penales.")

        winner_changed = previous_winner_id != (winner.pk if winner else None)
        downstream_conflict = has_conflicting_downstream_slot(tie, winner)
        requires_confirmation = (winner_changed and previous_winner_id is not None) or downstream_conflict
        if requires_confirmation:
            if not confirm_result_change:
                raise ValidationError(
                    "El resultado cambia al equipo clasificado. Revisa y confirma la actualización de las rondas posteriores."
                )
            _validate_downstream_rounds_unplayed(tie, winner=winner)
            _clear_downstream_results(tie)
            tie.home_penalties = None
            tie.away_penalties = None
            tie.decided_by_penalties = False

        tie.winner = winner
        tie.loser = tie.away_team if winner and winner == tie.home_team else tie.home_team if winner else None
        update_fields = ["winner", "loser", "updated_at"]
        if requires_confirmation:
            update_fields.extend(["home_penalties", "away_penalties", "decided_by_penalties"])
        tie.save(update_fields=update_fields)
        if requires_confirmation and confirm_result_change:
            sync_playoff_advancement(tie.playoff)
        else:
            _advance_tie(tie)
    return tie


def _downstream_round_codes(round_code):
    if round_code not in SCHEDULABLE_ROUNDS:
        return []
    downstream = SCHEDULABLE_ROUNDS[SCHEDULABLE_ROUNDS.index(round_code) + 1 :]
    if round_code in {PlayoffTie.ROUND_OF_64, PlayoffTie.ROUND_OF_32, PlayoffTie.ROUND_OF_16, PlayoffTie.QUARTERFINAL}:
        downstream = [*downstream, PlayoffTie.THIRD_PLACE]
    elif round_code == PlayoffTie.SEMIFINAL:
        downstream = [*downstream, PlayoffTie.THIRD_PLACE]
    return downstream


def _validate_downstream_rounds_unplayed(tie, *, winner):
    downstream_matches = Match.objects.filter(
        playoff_link__tie__round__in=_downstream_round_codes(tie.round),
        playoff_link__tie__playoff=tie.playoff,
    )
    if downstream_matches.exclude(status="scheduled").exists():
        raise ValidationError(
            "No se puede actualizar el cuadro: ya hay partidos disputados en una ronda posterior."
        )
    if winner is None and downstream_matches.exists():
        raise ValidationError(
            "Define la llave pendiente por penales antes de actualizar una ronda que ya tiene partidos programados."
        )


def has_conflicting_downstream_slot(tie, winner):
    if not tie.next_tie or not tie.next_slot:
        return False
    field_id = f"{tie.next_slot}_team_id"
    current_team_id = getattr(tie.next_tie, field_id)
    return current_team_id is not None and current_team_id != (winner.pk if winner else None)


def has_played_downstream_match(tie):
    downstream = tie.playoff.ties.filter(round__in=_downstream_round_codes(tie.round))
    return Match.objects.filter(playoff_link__tie__in=downstream).exclude(status="scheduled").exists()


def _clear_downstream_results(tie):
    downstream = tie.playoff.ties.filter(round__in=_downstream_round_codes(tie.round))
    downstream.update(
        winner=None,
        loser=None,
        home_penalties=None,
        away_penalties=None,
        decided_by_penalties=False,
    )


def _validate_completed_tie(tie):
    matches = get_tie_matches(tie)
    if not tie.home_team_id or not tie.away_team_id or not matches:
        raise ValidationError("La llave debe tener equipos y partidos asignados.")
    if any(match.status != "finished" for match in matches):
        raise ValidationError("Todos los partidos de la llave deben estar finalizados.")


def _advance_tie(tie):
    if not tie.winner:
        return
    if tie.round == PlayoffTie.SEMIFINAL:
        final = tie.playoff.ties.filter(round=PlayoffTie.FINAL).first()
        if final:
            field = "home_team" if tie.position == 1 else "away_team"
            setattr(final, field, tie.winner)
            final.save(update_fields=[field, "updated_at"])
        third_place = tie.playoff.ties.filter(round=PlayoffTie.THIRD_PLACE).first()
        if third_place and tie.loser:
            field = "home_team" if tie.position == 1 else "away_team"
            setattr(third_place, field, tie.loser)
            third_place.save(update_fields=[field, "updated_at"])
        return
    if not tie.next_tie:
        return
    next_tie = PlayoffTie.objects.select_for_update().get(pk=tie.next_tie_id)
    field = "home_team" if tie.next_slot == "home" else "away_team"
    setattr(next_tie, field, tie.winner)
    next_tie.save(update_fields=[field, "updated_at"])