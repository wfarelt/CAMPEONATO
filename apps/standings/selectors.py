"""Read-side helpers for standings tables and ranking data."""

from django.db.models import F, Q, Sum

from apps.matches.models import Match
from apps.teams.models import Team


def calculate_team_standing(team, include_adjustments=True, category=None):
	"""Compute standings metrics for a single team."""
	championship_category = category or team.category
	matches_played = Match.objects.filter(
		Q(home_team=team, status="finished") | Q(away_team=team, status="finished"),
		home_team__category=championship_category,
		away_team__category=championship_category,
	)
	won = matches_played.filter(
		Q(home_team=team, home_score__gt=F("away_score"))
		| Q(away_team=team, away_score__gt=F("home_score"))
	).count()
	drawn = matches_played.filter(home_score=F("away_score")).count()
	lost = matches_played.count() - won - drawn

	goals_for = matches_played.filter(home_team=team).aggregate(Sum("home_score"))["home_score__sum"] or 0
	goals_for += matches_played.filter(away_team=team).aggregate(Sum("away_score"))["away_score__sum"] or 0

	goals_against = matches_played.filter(home_team=team).aggregate(Sum("away_score"))["away_score__sum"] or 0
	goals_against += matches_played.filter(away_team=team).aggregate(Sum("home_score"))["home_score__sum"] or 0

	points = won * 3 + drawn
	if include_adjustments:
		adjustments = team.points_adjustments.aggregate(total=Sum("points"))["total"] or 0
		points += adjustments

	return {
		"team": team.name,
		"category": championship_category,
		"matches_played": matches_played.count(),
		"won": won,
		"drawn": drawn,
		"lost": lost,
		"goals_for": goals_for,
		"goals_against": goals_against,
		"goal_difference": goals_for - goals_against,
		"points": points,
	}


def get_sorted_standings(include_adjustments=True, category=None):
	teams_qs = Team.objects.all()
	if category:
		teams_qs = teams_qs.filter(category=category)
	standings = [
		calculate_team_standing(team, include_adjustments=include_adjustments, category=category)
		for team in teams_qs
	]
	return sorted(
		standings,
		key=lambda item: (-item["points"], -item["goal_difference"], -item["goals_for"]),
	)


def get_last_results(team, exclude_match=None, n=5, category=None):
	championship_category = category or team.category
	matches = Match.objects.filter(
		(Q(home_team=team) | Q(away_team=team)) & Q(status="finished"),
		home_team__category=championship_category,
		away_team__category=championship_category,
	)
	if exclude_match:
		matches = matches.exclude(pk=exclude_match.pk)
	matches = matches.order_by("-date", "-time")[:n]

	results = []
	for match in matches:
		if match.home_team == team:
			if match.home_score > match.away_score:
				results.append("G")
			elif match.home_score == match.away_score:
				results.append("E")
			else:
				results.append("P")
		else:
			if match.away_score > match.home_score:
				results.append("G")
			elif match.away_score == match.home_score:
				results.append("E")
			else:
				results.append("P")
	return results


def get_opponents_with_points(team):
	all_teams = set(Team.objects.filter(category=team.category).exclude(pk=team.pk))
	played_matches = Match.objects.filter(
		Q(home_team=team) | Q(away_team=team),
		status="finished",
		home_team__category=team.category,
		away_team__category=team.category,
	)

	already_played = set()
	for match in played_matches:
		if match.home_team == team:
			already_played.add(match.away_team)
		else:
			already_played.add(match.home_team)

	opponents_data = []
	for opponent in all_teams - already_played:
		standing = calculate_team_standing(opponent, include_adjustments=False, category=team.category)
		opponents_data.append({"team": opponent, "points": standing["points"]})

	return sorted(opponents_data, key=lambda item: -item["points"])


def get_results_by_team(team):
	matches = Match.objects.filter(
		Q(home_team=team) | Q(away_team=team),
		status="finished",
		home_team__category=team.category,
		away_team__category=team.category,
	).order_by("-date", "-time")

	results = []
	for match in matches:
		is_home = match.home_team == team
		opponent = match.away_team if is_home else match.home_team
		goals_for = match.home_score if is_home else match.away_score
		goals_against = match.away_score if is_home else match.home_score

		if goals_for > goals_against:
			result = "G"
		elif goals_for == goals_against:
			result = "E"
		else:
			result = "P"

		results.append(
			{
				"date": match.date,
				"opponent": opponent.name,
				"is_home": is_home,
				"goals_for": goals_for,
				"goals_against": goals_against,
				"result": result,
			}
		)
	return results
