from django.contrib import admin

from apps.matches.models import Match, MatchEvent, PointsAdjustment


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "home_team", "away_team", "court", "home_score", "away_score", "status", "date", "match_day")
    list_filter = ("status", "date", "match_day", "court")


@admin.register(PointsAdjustment)
class PointsAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("id", "team", "match", "points", "reason", "date")
    list_filter = ("date", "team")
    search_fields = ("team__name", "reason")


@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ("id", "match", "player", "team", "event_type", "minute", "created_at")
    list_filter = ("event_type", "team", "match")
    search_fields = ("match__home_team__name", "match__away_team__name", "player__name", "team__name")
    raw_id_fields = ("player", "match")
