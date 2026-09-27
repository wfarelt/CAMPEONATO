from django.contrib import admin
from django.db.models import Q
from django.http import JsonResponse
from django.urls import path, reverse

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

    class Media:
        js = ("matches/js/points_adjustment_admin.js",)

    def get_urls(self):
        urls = [
            path(
                "matches-by-team/",
                self.admin_site.admin_view(self.matches_by_team_view),
                name="matches_pointsadjustment_matches_by_team",
            ),
        ]
        return urls + super().get_urls()

    def matches_by_team_view(self, request):
        team_id = request.GET.get("team_id")
        matches = Match.objects.filter(Q(home_team_id=team_id) | Q(away_team_id=team_id)).order_by("-date")
        data = [{"id": match.pk, "label": str(match)} for match in matches]
        return JsonResponse(data, safe=False)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "match":
            team_id = request.GET.get("team") or request.POST.get("team")
            if team_id:
                kwargs["queryset"] = Match.objects.filter(Q(home_team_id=team_id) | Q(away_team_id=team_id))
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "match":
            formfield.widget.attrs["data-filter-url"] = reverse(
                "admin:matches_pointsadjustment_matches_by_team"
            )
        return formfield


@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ("id", "match", "player", "team", "event_type", "minute", "created_at")
    list_filter = ("event_type", "team", "match")
    search_fields = ("match__home_team__name", "match__away_team__name", "player__name", "team__name")
    raw_id_fields = ("player", "match")
