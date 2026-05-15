"""Business logic for matches app."""

from apps.matches.models import Match
from apps.standings.selectors import get_last_results
from apps.tournaments.models import MatchDay


DEFAULT_TEAM_LOGO = "/static/tournament/img/default_logo.jpg"


def build_home_context(category):
	latest_matchday = MatchDay.objects.filter(category=category).prefetch_related("matches__home_team", "matches__away_team").first()
	category_matches = Match.objects.filter(home_team__category=category, away_team__category=category)

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
		timeline_matches.append(
			{
				"home_team": match.home_team.name,
				"away_team": match.away_team.name,
				"home_short": match.home_team.name[:3].upper(),
				"away_short": match.away_team.name[:3].upper(),
				"home_score": match.home_score if is_finished else "-",
				"away_score": match.away_score if is_finished else "-",
				"status": "Finalizado" if is_finished else "Programado",
				"time": match.time.strftime("%H:%M"),
				"is_finished": is_finished,
			}
		)

	if matches_qs.exists():
		highlighted = matches_qs.filter(status="finished").order_by("-time").first() or matches_qs.order_by("time").first()
		is_finished = highlighted.status == "finished"
		featured_match = {
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

	return {
		"timeline_title": timeline_title,
		"timeline_matches": timeline_matches,
		"featured_match": featured_match,
	}


def build_matches_context(category):
	matches_scope = Match.objects.filter(home_team__category=category, away_team__category=category)
	matches_pending = matches_scope.filter(status="scheduled").order_by("date", "time")
	matches_finished = matches_scope.filter(status="finished").order_by("date", "time")

	matches_pending_list = []
	for match in matches_pending:
		matches_pending_list.append(
			{
				"home_team": match.home_team.name,
				"home_team_logo": match.home_team.logo.url if match.home_team.logo else DEFAULT_TEAM_LOGO,
				"home_team_last_results": get_last_results(match.home_team, exclude_match=match, category=category),
				"away_team": match.away_team.name,
				"away_team_logo": match.away_team.logo.url if match.away_team.logo else DEFAULT_TEAM_LOGO,
				"away_team_last_results": get_last_results(match.away_team, exclude_match=match, category=category),
				"date": f"{match.date} {match.time.strftime('%H:%M')}",
			}
		)

	return {
		"matches_pending": matches_pending_list,
		"matches_finished": matches_finished,
	}
