"""Admin registration for the payments app."""

from django.contrib import admin

from apps.payments.models import CardPayment


@admin.register(CardPayment)
class CardPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "get_player", "get_team", "get_event_type", "amount", "paid", "paid_date", "created_at")
    list_filter = ("paid", "match_event__event_type", "match_event__team")
    search_fields = ("match_event__player__name", "match_event__team__name", "notes")
    raw_id_fields = ("match_event",)
    date_hierarchy = "created_at"

    @admin.display(description="Jugador")
    def get_player(self, obj):
        return obj.match_event.player

    @admin.display(description="Equipo")
    def get_team(self, obj):
        return obj.match_event.team

    @admin.display(description="Tipo")
    def get_event_type(self, obj):
        return obj.match_event.get_event_type_display()
