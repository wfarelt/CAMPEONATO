from django.contrib import admin
from .models import Team, Player, Match, PointsAdjustment, MatchDay

# Mostrar id y nombre del equipo en el panel de administración
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'home_team', 'away_team', 'home_score', 'away_score', 'status', 'date', 'match_day')
    list_filter = ('status', 'date', 'match_day')
    
class MatchInline(admin.TabularInline):
    model = Match
    extra = 1
    fields = ('home_team', 'away_team', 'time', 'home_score', 'away_score', 'status')
    readonly_fields = []

class MatchDayAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'matches_count')
    fields = ('date', 'description')
    inlines = [MatchInline]
    
    def matches_count(self, obj):
        return obj.matches.count()
    matches_count.short_description = 'Número de partidos'

admin.site.register(MatchDay, MatchDayAdmin)
admin.site.register(Team)
admin.site.register(Player)
admin.site.register(Match, MatchAdmin)
admin.site.register(PointsAdjustment)