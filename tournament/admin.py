from django.contrib import admin
from .models import Team, Player, Match
# Register your models here.

# Mostrar id y nombre del equipo en el panel de administración
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'home_team', 'away_team', 'home_score', 'away_score')
    
admin.site.register(Team)
admin.site.register(Player)
admin.site.register(Match, MatchAdmin)