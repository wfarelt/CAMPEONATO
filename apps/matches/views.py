from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from apps.core.categories import get_request_championship_category
from apps.matches.forms import MatchEventForm, MatchResultForm
from apps.matches.models import Match, MatchEvent
from apps.matches.services import build_home_context, build_matches_context, build_statistics_context
from apps.teams.models import Player
from apps.notifications.services import create_and_dispatch_notification
from apps.notifications.models import NotificationAudienceType, NotificationCategory
import logging

logger = logging.getLogger(__name__)


def home(request):
    category = get_request_championship_category(request)
    return render(request, "matches/dashboard.html", build_home_context(category=category))


@login_required
def matches_view(request):
    category = get_request_championship_category(request)
    selected_matchday_slug = request.GET.get("matchday")
    return render(
        request,
        "matches/matches.html",
        build_matches_context(category=category, selected_matchday_slug=selected_matchday_slug),
    )


@login_required
def statistics(request):
    category = get_request_championship_category(request)
    return render(request, "matches/statistics.html", build_statistics_context(category=category))


@login_required
def match_detail_view(request, match_slug):
    category = get_request_championship_category(request)
    match = get_object_or_404(
        Match.objects.select_related("home_team", "away_team", "match_day"),
        slug=match_slug,
        home_team__category=category,
        away_team__category=category,
    )
    return render(request, "matches/match_detail.html", {"match": match})


@login_required
def match_result_view(request, match_slug):
    category = get_request_championship_category(request)
    match = get_object_or_404(
        Match.objects.select_related("home_team", "away_team", "match_day"),
        slug=match_slug,
        home_team__category=category,
        away_team__category=category,
    )
    players = Player.objects.filter(team__in=[match.home_team, match.away_team]).select_related("team").order_by(
        "team__name",
        "name",
    )
    events = match.events.select_related("player", "team").order_by("-created_at", "-id")
    match_form = MatchResultForm(instance=match)
    event_form = MatchEventForm(players=players)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_match":
            match_form = MatchResultForm(request.POST, instance=match)
            if match_form.is_valid():
                # Detect status change to 'finished' to send notification
                new_status = match_form.cleaned_data.get("status")
                was_finished = match.status == "finished"
                match_form.save()

                # Send notification when the saved status is 'finished'
                if new_status == "finished":
                    # Build absolute URL to match detail
                    try:
                        detail_path = reverse("match_detail", kwargs={"match_slug": match.slug})
                        detail_url = request.build_absolute_uri(detail_path)
                    except Exception:
                        detail_url = ""
                    # Build message with jornada (match_day), teams and result
                    match.refresh_from_db()
                    if match.match_day and getattr(match.match_day, "description", ""):
                        matchday_label = match.match_day.description
                    elif match.match_day and getattr(match.match_day, "date", None):
                        matchday_label = match.match_day.date.strftime("%d-%m-%Y")
                    else:
                        matchday_label = ""
                    title = "Partido finalizado"
                    message = f"Jornada {matchday_label}: {match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}"
                    push_url = detail_url or ""
                    logger.warning("Dispatching match-finished notification: title=%s message=%s url=%s", title, message, push_url)
                    try:
                        create_and_dispatch_notification(
                            title=title,
                            message=message,
                            category=NotificationCategory.MATCH,
                            audience_type=NotificationAudienceType.ALL,
                            created_by=request.user if hasattr(request, "user") else None,
                            send_push=True,
                            push_url=push_url,
                        )
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logger.exception("Failed to dispatch match-finished notification: %s", exc)
                        # continue without failing the request

                return redirect("matches")

        elif action == "add_event":
            event_form = MatchEventForm(request.POST, players=players)
            if event_form.is_valid():
                event_type = request.POST.get("event_type") or MatchEvent.GOAL
                created_event = event_form.save(commit=False)
                created_event.match = match
                created_event.event_type = event_type
                created_event.team = created_event.player.team
                with transaction.atomic():
                    created_event.save()
                    if event_type == MatchEvent.GOAL:
                        Player.objects.filter(pk=created_event.player_id).update(goals_scored=F("goals_scored") + 1)
                        if created_event.team_id == match.home_team_id:
                            Match.objects.filter(pk=match.pk).update(home_score=F("home_score") + 1)
                        else:
                            Match.objects.filter(pk=match.pk).update(away_score=F("away_score") + 1)
                return redirect("match_result", match_slug=match.slug)

        elif action == "delete_event":
            event = get_object_or_404(MatchEvent, pk=request.POST.get("event_id"), match=match)
            with transaction.atomic():
                if event.event_type == MatchEvent.GOAL:
                    Player.objects.filter(pk=event.player_id, goals_scored__gt=0).update(goals_scored=F("goals_scored") - 1)
                    if event.team_id == match.home_team_id and match.home_score > 0:
                        Match.objects.filter(pk=match.pk, home_score__gt=0).update(home_score=F("home_score") - 1)
                    elif event.team_id == match.away_team_id and match.away_score > 0:
                        Match.objects.filter(pk=match.pk, away_score__gt=0).update(away_score=F("away_score") - 1)
                event.delete()
            return redirect("match_result", match_slug=match.slug)

        else:
            match_form = MatchResultForm(instance=match)
            event_form = MatchEventForm(players=players)

    return render(
        request,
        "matches/match_result.html",
        {
            "match": Match.objects.select_related("home_team", "away_team", "match_day").prefetch_related(
                "events__player",
                "events__team",
            ).get(pk=match.pk),
            "match_form": match_form,
            "event_form": event_form,
            "events": events,
            "goal_events": events.filter(event_type=MatchEvent.GOAL),
            "card_events": events.filter(event_type__in=[MatchEvent.YELLOW_CARD, MatchEvent.RED_CARD]),
            "players": players,
        },
    )
