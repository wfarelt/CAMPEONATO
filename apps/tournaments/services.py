"""Write-side business logic for tournaments app."""

from django.db.models import Q

from apps.matches.models import Match
from apps.teams.models import Team


def save_matchday_with_matches(matchday_form, formset):
	"""Persist a matchday and its related matches from a bound formset."""
	matchday = matchday_form.save()

	instances = formset.save(commit=False)
	for instance in instances:
		instance.date = matchday.date
		instance.match_day = matchday
		instance.save()

	for obj in formset.deleted_objects:
		obj.delete()

	return matchday


def _max_matching_size(team_ids, invalid_pairs):
	"""Return the maximum cardinality matching possible on ``team_ids``.

	A team may appear in at most one pair and every pair must not be in
	``invalid_pairs`` (order independent, i.e. ``frozenset``).

	The implementation uses a bitmask dynamic-programming approach so it
	scales well for the typical number of teams in a local championship.
	"""
	n = len(team_ids)
	if n < 2:
		return 0

	index_by_id = {team_id: idx for idx, team_id in enumerate(team_ids)}
	invalid_pair_set = set()
	for pair in invalid_pairs:
		members = list(pair)
		if len(members) == 2 and members[0] in index_by_id and members[1] in index_by_id:
			i, j = sorted((index_by_id[members[0]], index_by_id[members[1]]))
			invalid_pair_set.add((i, j))

	full_mask = (1 << n) - 1
	memo = {}

	def dp(mask):
		if mask in memo:
			return memo[mask]
		if mask == 0:
			return 0

		# Take the lowest set bit as the first vertex of the pair.
		lsb = mask & -mask
		i = lsb.bit_length() - 1
		mask_without_i = mask ^ (1 << i)

		best = dp(mask_without_i)
		for j in range(i + 1, n):
			if mask_without_i & (1 << j) and (i, j) not in invalid_pair_set:
				best = max(best, 1 + dp(mask_without_i ^ (1 << j)))

		memo[mask] = best
		return best

	return dp(full_mask)


def _find_matching(requested, team_ids, invalid_pairs, team_match_counts, team_names):
	"""Return ``requested`` disjoint pairs from ``team_ids``.

	Pairs are not repeated with respect to ``invalid_pairs`` and no team is
	used in more than one pair.  The returned list has ``requested`` pairs or
	``None`` when it is impossible.
	"""
	if requested == 0:
		return []
	if len(team_ids) < 2 * requested:
		return None

	available_set = set(team_ids)
	partners_for = {
		team_id: [
			other_id
			for other_id in team_ids
			if other_id != team_id
			and frozenset((team_id, other_id)) not in invalid_pairs
		]
		for team_id in team_ids
	}

	def backtrack(remaining_set, matches_left):
		if matches_left == 0:
			return []
		if len(remaining_set) < 2 * matches_left:
			return None

		# Minimum Remaining Values heuristic for fast backtracking.
		first = min(
			remaining_set,
			key=lambda team_id: (
				len([p for p in partners_for[team_id] if p in remaining_set]),
				team_match_counts[team_id],
				team_names[team_id],
				team_id,
			),
		)
		options = [other_id for other_id in partners_for[first] if other_id in remaining_set]
		options.sort(
			key=lambda other_id: (
				team_match_counts[other_id],
				team_names[other_id],
				other_id,
			)
		)

		for second in options:
			new_set = remaining_set - {first, second}
			sub = backtrack(new_set, matches_left - 1)
			if sub is not None:
				return [(first, second)] + sub
		return None

	return backtrack(available_set, requested)


def recommend_matches_for_matchday(category, requested_match_count):
	"""Return suggested team pairings prioritizing teams with fewer total matches.

	The recommendation never repeats an historical pairing (home/away order is
	irrelevant) and never assigns the same team to more than one recommended
	match.  If ``requested_match_count`` cannot be fulfilled without breaking
	those rules, the returned dict contains an explanatory message and no
	matches.
	"""
	try:
		requested = max(int(requested_match_count or 0), 0)
	except (TypeError, ValueError):
		requested = 0

	base_result = {
		"possible": True,
		"matches": [],
		"message": "",
		"max_possible": 0,
	}

	if requested == 0:
		return base_result

	available_teams = list(
		Team.objects.filter(category=category, is_available_for_matchday=True).order_by("name")
	)
	if len(available_teams) < 2:
		return {
			**base_result,
			"possible": False,
			"message": "No hay suficientes equipos disponibles para recomendar partidos.",
		}

	team_ids = [team.id for team in available_teams]
	team_names = {team.id: team.name.lower() for team in available_teams}
	team_match_counts = {team_id: 0 for team_id in team_ids}
	played_pairs = set()

	matches = Match.objects.filter(
		home_team__category=category,
		away_team__category=category,
	).filter(Q(home_team_id__in=team_ids) | Q(away_team_id__in=team_ids))

	for match in matches:
		if match.home_team_id in team_match_counts:
			team_match_counts[match.home_team_id] += 1
		if match.away_team_id in team_match_counts:
			team_match_counts[match.away_team_id] += 1
		played_pairs.add(frozenset((match.home_team_id, match.away_team_id)))

	max_possible = _max_matching_size(team_ids, played_pairs)

	if requested > max_possible:
		return {
			**base_result,
			"possible": False,
			"message": (
				f"No se pueden recomendar {requested} partidos sin repetir. "
				f"Solo es posible asignar {max_possible} partido(s) sin repetir equipos ni enfrentamientos."
			),
			"max_possible": max_possible,
		}

	pairs = _find_matching(requested, team_ids, played_pairs, team_match_counts, team_names)
	if pairs is None:
		return {
			**base_result,
			"possible": False,
			"message": (
				f"No se pudieron armar {requested} partidos sin repetir. "
				f"Solo es posible asignar {max_possible} partido(s) sin repetir equipos ni enfrentamientos."
			),
			"max_possible": max_possible,
		}

	return {
		**base_result,
		"matches": [{"home_team": home_id, "away_team": away_id} for home_id, away_id in pairs],
		"max_possible": max_possible,
	}
