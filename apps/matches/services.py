"""Business logic for matches app."""

from django.db.models import Sum

from apps.matches.models import Match
from apps.sponsors.models import Sponsor
from apps.standings.services import build_standings
from apps.standings.selectors import get_last_results
from apps.teams.models import Player
from apps.tournaments.models import MatchDay


DEFAULT_TEAM_LOGO = "/static/tournament/img/default_logo.jpg"


def get_top_scoring_teams(category, limit=5):
	"""Return teams ordered by goals scored in finished matches."""
	finished_matches = Match.objects.filter(
		home_team__category=category,
		away_team__category=category,
		status="finished",
	).select_related("home_team", "away_team")

	teams_data = {}

	for match in finished_matches:
		home_team = match.home_team
		away_team = match.away_team

		if home_team.id not in teams_data:
			teams_data[home_team.id] = {
				"team_name": home_team.name,
				"team_logo": home_team.logo.url if home_team.logo else DEFAULT_TEAM_LOGO,
				"goals": 0,
			}

		if away_team.id not in teams_data:
			teams_data[away_team.id] = {
				"team_name": away_team.name,
				"team_logo": away_team.logo.url if away_team.logo else DEFAULT_TEAM_LOGO,
				"goals": 0,
			}

		teams_data[home_team.id]["goals"] += match.home_score
		teams_data[away_team.id]["goals"] += match.away_score

	sorted_teams = sorted(
		teams_data.values(),
		key=lambda item: (-item["goals"], item["team_name"]),
	)[:limit]

	for position, team in enumerate(sorted_teams, start=1):
		team["position"] = position

	return sorted_teams


def get_best_goalkeepers(category, limit=5):
	"""Retorna equipos con menos goles recibidos (mejores arqueros)."""
	finished_matches = Match.objects.filter(
		home_team__category=category,
		away_team__category=category,
		status="finished"
	).select_related("home_team", "away_team")
	
	teams_data = {}
	
	for match in finished_matches:
		home_team = match.home_team
		away_team = match.away_team
		
		if home_team.id not in teams_data:
			teams_data[home_team.id] = {"team": home_team, "goals_against": 0, "matches": 0}
		if away_team.id not in teams_data:
			teams_data[away_team.id] = {"team": away_team, "goals_against": 0, "matches": 0}
		
		teams_data[home_team.id]["goals_against"] += match.away_score
		teams_data[home_team.id]["matches"] += 1
		
		teams_data[away_team.id]["goals_against"] += match.home_score
		teams_data[away_team.id]["matches"] += 1
	
	sorted_teams = sorted(
		teams_data.values(),
		key=lambda x: x["goals_against"]
	)[:limit]
	
	return sorted_teams


def get_top_scorers(category, limit=5):
	"""Return top goal scorers from players in the selected category."""
	top_players = (
		Player.objects.filter(team__category=category)
		.select_related("team")
		.order_by("-goals_scored", "name")[:limit]
	)

	ranking = []
	for position, player in enumerate(top_players, start=1):
		ranking.append(
			{
				"position": position,
				"player_name": player.name,
				"team_name": player.team.name,
				"goals": player.goals_scored,
			}
		)

	return ranking


def build_home_context(category):
	latest_matchday = MatchDay.objects.filter(category=category).prefetch_related("matches__home_team", "matches__away_team").first()
	category_matches = Match.objects.filter(home_team__category=category, away_team__category=category)
	finished_matches = category_matches.filter(status="finished")
	scheduled_matches = category_matches.filter(status="scheduled")
	goals_data = finished_matches.aggregate(home_goals=Sum("home_score"), away_goals=Sum("away_score"))
	total_goals = (goals_data["home_goals"] or 0) + (goals_data["away_goals"] or 0)
	next_match = scheduled_matches.select_related("home_team", "away_team").order_by("date", "time").first()

	timeline_matches = []
	timeline_title = "Ultima Jornada"
	featured_match = None

	if latest_matchday and latest_matchday.matches.exists():
		matches_qs = latest_matchday.matches.select_related("home_team", "away_team").order_by("time")
		timeline_title = latest_matchday.description or f"Jornada del {latest_matchday.date.strftime('%d/%m/%Y')}"
	else:
		latest_match_date = category_matches.order_by("-date").values_list("date", flat=True).first()
		matches_qs = Match.objects.none()
		if latest_match_date:
			matches_qs = category_matches.filter(date=latest_match_date).select_related("home_team", "away_team").order_by("time")
			timeline_title = f"Jornada del {latest_match_date.strftime('%d/%m/%Y')}"

	for match in matches_qs:
		is_finished = match.status == "finished"
		if match.match_day:
			matchday_label = match.match_day.description or f"Jornada {match.match_day.date.strftime('%d/%m/%Y')}"
		else:
			matchday_label = f"Jornada {match.date.strftime('%d/%m/%Y')}"
		timeline_matches.append(
			{
				"slug": match.slug,
				"home_team": match.home_team.name,
				"away_team": match.away_team.name,
				"home_logo": match.home_team.logo.url if match.home_team.logo else DEFAULT_TEAM_LOGO,
				"away_logo": match.away_team.logo.url if match.away_team.logo else DEFAULT_TEAM_LOGO,
				"home_score": match.home_score if is_finished else "-",
				"away_score": match.away_score if is_finished else "-",
				"status": "Finalizado" if is_finished else "Programado",
				"date": match.date.strftime("%d/%m/%Y"),
				"time": match.time.strftime("%H:%M"),
				"court": match.get_court_display(),
				"matchday_label": matchday_label,
				"is_finished": is_finished,
			}
		)

	if matches_qs.exists():
		highlighted = matches_qs.filter(status="finished").order_by("-time").first() or matches_qs.order_by("time").first()
		is_finished = highlighted.status == "finished"
		featured_match = {
			"slug": highlighted.slug,
			"home_team": highlighted.home_team.name,
			"away_team": highlighted.away_team.name,
			"home_logo": highlighted.home_team.logo.url if highlighted.home_team.logo else None,
			"away_logo": highlighted.away_team.logo.url if highlighted.away_team.logo else None,
			"home_score": highlighted.home_score if is_finished else "-",
			"away_score": highlighted.away_score if is_finished else "-",
			"status": "FINALIZADO" if is_finished else "PROGRAMADO",
			"status_class": "text-accent-green bg-accent-green/20" if is_finished else "text-primary bg-primary/20",
			"date": highlighted.date.strftime("%d/%m/%Y"),
			"time": highlighted.time.strftime("%H:%M"),
			"is_finished": is_finished,
		}

	quick_standings = build_standings(category=category, include_adjustments=True)[:5]
	top_scoring_teams = get_top_scoring_teams(category=category, limit=5)
	sponsors = list(Sponsor.objects.filter(is_active=True).only("name", "image").order_by("name"))

	return {
		"timeline_title": timeline_title,
		"timeline_matches": timeline_matches,
		"featured_match": featured_match,
		"summary_cards": [
			{"label": "Partidos Totales", "value": category_matches.count()},
			{"label": "Finalizados", "value": finished_matches.count()},
			{"label": "Programados", "value": scheduled_matches.count()},
			{"label": "Goles", "value": total_goals},
		],
		"next_match": {
			"home_team": next_match.home_team.name,
			"away_team": next_match.away_team.name,
			"date": next_match.date.strftime("%d/%m/%Y"),
			"time": next_match.time.strftime("%H:%M"),
			"court": next_match.get_court_display(),
		} if next_match else None,
		"top_scoring_teams": top_scoring_teams,
		"quick_standings": quick_standings,
		"sponsors": sponsors,
	}


def build_matches_context(category, selected_matchday_slug=None):
	matches_scope = Match.objects.filter(home_team__category=category, away_team__category=category)
	matches_pending = matches_scope.filter(status="scheduled").order_by("date", "time")
	matches_finished = matches_scope.filter(status="finished").order_by("date", "time")
	matchdays = MatchDay.objects.filter(category=category)

	selected_matchday = None
	if selected_matchday_slug:
		selected_matchday = matchdays.filter(slug=selected_matchday_slug).first()

	if selected_matchday:
		matches_finished = matches_finished.filter(match_day=selected_matchday)

	matches_pending_list = []
	for match in matches_pending:
		if match.match_day:
			matchday_label = match.match_day.description or f"Jornada {match.match_day.date.strftime('%d/%m/%Y')}"
		else:
			matchday_label = f"Jornada {match.date.strftime('%d/%m/%Y')}"

		matches_pending_list.append(
			{
				"slug": match.slug,
				"home_team": match.home_team.name,
				"home_team_logo": match.home_team.logo.url if match.home_team.logo else DEFAULT_TEAM_LOGO,
				"home_team_last_results": get_last_results(match.home_team, exclude_match=match, category=category),
				"away_team": match.away_team.name,
				"away_team_logo": match.away_team.logo.url if match.away_team.logo else DEFAULT_TEAM_LOGO,
				"away_team_last_results": get_last_results(match.away_team, exclude_match=match, category=category),
				"matchday_label": matchday_label,
				"court": match.get_court_display(),
				"date": match.date,
				"time": match.time.strftime('%H:%M'),
			}
		)

	return {
		"matches_pending": matches_pending_list,
		"matches_finished": matches_finished,
		"matchdays": matchdays,
		"selected_matchday_slug": selected_matchday.slug if selected_matchday else "",
	}


def build_statistics_context(category):
	matches_scope = Match.objects.filter(home_team__category=category, away_team__category=category)
	finished_matches = matches_scope.filter(status="finished")
	finished_count = finished_matches.count()
	goals_data = finished_matches.aggregate(home_goals=Sum("home_score"), away_goals=Sum("away_score"))
	total_goals = (goals_data["home_goals"] or 0) + (goals_data["away_goals"] or 0)
	avg_goals_per_match = (total_goals / finished_count) if finished_count else 0
	
	best_gk = get_best_goalkeepers(category, limit=5)
	top_scorers = get_top_scorers(category, limit=5)

	return {
		"total_matches": matches_scope.count(),
		"total_goals": total_goals,
		"avg_goals_per_match": avg_goals_per_match,
		"total_yellow_cards": 0,
		"avg_yellow_cards_per_match": 0,
		"total_red_cards": 0,
		"avg_red_cards_per_match": 0,
		"best_goalkeepers": best_gk,
		"top_scorers": top_scorers,
	}
