from django.contrib import admin

from apps.matches.models import Match
from apps.tournaments.models import MatchDay, Tournament, TournamentTeam


class TournamentTeamInline(admin.TabularInline):
    model = TournamentTeam
    extra = 1
    raw_id_fields = ("team",)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "category", "status", "start_date", "end_date")
    list_filter = ("category", "status", "season")
    search_fields = ("name", "season")
    inlines = [TournamentTeamInline]


class MatchInline(admin.TabularInline):
    model = Match
    extra = 1
    fields = ("home_team", "away_team", "court", "time", "home_score", "away_score", "status")


@admin.register(MatchDay)
class MatchDayAdmin(admin.ModelAdmin):
    list_display = ("date", "tournament", "category", "description", "is_visible", "matches_count")
    list_filter = ("tournament", "category", "is_visible")
    fields = ("tournament", "category", "date", "description", "is_visible")
    inlines = [MatchInline]

    def matches_count(self, obj):
        return obj.matches.count()

    matches_count.short_description = "Numero de partidos"
