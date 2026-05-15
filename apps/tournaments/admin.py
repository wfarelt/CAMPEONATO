from django.contrib import admin

from apps.matches.models import Match
from apps.tournaments.models import MatchDay


class MatchInline(admin.TabularInline):
    model = Match
    extra = 1
    fields = ("home_team", "away_team", "time", "home_score", "away_score", "status")


@admin.register(MatchDay)
class MatchDayAdmin(admin.ModelAdmin):
    list_display = ("date", "category", "description", "matches_count")
    list_filter = ("category",)
    fields = ("category", "date", "description")
    inlines = [MatchInline]

    def matches_count(self, obj):
        return obj.matches.count()

    matches_count.short_description = "Numero de partidos"
