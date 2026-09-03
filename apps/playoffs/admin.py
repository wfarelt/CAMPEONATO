from django.contrib import admin

from apps.playoffs.models import LeagueSettings, Playoff, PlayoffTie


@admin.register(LeagueSettings)
class LeagueSettingsAdmin(admin.ModelAdmin):
    list_display = ("category", "teams_classified", "playoffs_enabled", "playoffs_home_and_away", "third_place_match")
    list_filter = ("playoffs_enabled", "playoffs_home_and_away", "third_place_match")


class PlayoffTieInline(admin.TabularInline):
    model = PlayoffTie
    extra = 0
    fields = ("round", "position", "home_team", "away_team", "first_leg", "second_leg", "winner", "loser")
    readonly_fields = ("winner", "loser")


@admin.register(Playoff)
class PlayoffAdmin(admin.ModelAdmin):
    list_display = ("category", "settings", "is_active", "created_at")
    list_filter = ("category", "is_active")
    inlines = [PlayoffTieInline]


@admin.register(PlayoffTie)
class PlayoffTieAdmin(admin.ModelAdmin):
    list_display = ("playoff", "round", "position", "home_team", "away_team", "winner", "decided_by_penalties")
    list_filter = ("round", "decided_by_penalties")
    search_fields = ("home_team__name", "away_team__name")