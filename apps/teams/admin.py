from django.contrib import admin

from apps.teams.models import Player, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "coach", "manager", "is_available_for_matchday")
    list_filter = ("category", "is_available_for_matchday")
    search_fields = ("name", "coach", "manager__username")
    raw_id_fields = ("manager",)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "number", "position", "team")
    list_filter = ("position", "team")
    search_fields = ("name", "team__name")
