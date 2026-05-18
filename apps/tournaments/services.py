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


def recommend_matches_for_matchday(category, requested_match_count):
	"""Return suggested team pairings prioritizing teams with fewer total matches."""
	try:
		requested = max(int(requested_match_count or 0), 0)
	except (TypeError, ValueError):
		requested = 0

	if requested == 0:
		return []

	available_teams = list(
		Team.objects.filter(category=category, is_available_for_matchday=True).order_by("name")
	)
	if len(available_teams) < 2:
		return []

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

	recommendations = []
	used_in_round = set()

	while len(recommendations) < requested:
		available_in_round = [team_id for team_id in team_ids if team_id not in used_in_round]
		if len(available_in_round) < 2:
			if used_in_round:
				used_in_round = set()
				continue
			break

		home_team_id = min(
			available_in_round,
			key=lambda team_id: (team_match_counts[team_id], team_names[team_id], team_id),
		)

		opponents = [team_id for team_id in available_in_round if team_id != home_team_id]
		away_team_id = min(
			opponents,
			key=lambda team_id: (
				frozenset((home_team_id, team_id)) in played_pairs,
				team_match_counts[team_id],
				team_names[team_id],
				team_id,
			),
		)

		recommendations.append(
			{
				"home_team": home_team_id,
				"away_team": away_team_id,
			}
		)

		team_match_counts[home_team_id] += 1
		team_match_counts[away_team_id] += 1
		played_pairs.add(frozenset((home_team_id, away_team_id)))
		used_in_round.update({home_team_id, away_team_id})

	return recommendations
