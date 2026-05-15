from django.contrib import admin

from apps.matches.models import Match, PointsAdjustment


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "home_team", "away_team", "home_score", "away_score", "status", "date", "match_day")
    list_filter = ("status", "date", "match_day")


@admin.register(PointsAdjustment)
class PointsAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("id", "team", "match", "points", "reason", "date")
    list_filter = ("date", "team")
    search_fields = ("team__name", "reason")
