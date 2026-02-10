from django.db import models

class MatchDay(models.Model):
    date = models.DateField(unique=True, verbose_name="Match Day Date")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Matchday - {self.date}"

    class Meta:
        ordering = ['-date']
        verbose_name = "Match Day"
        verbose_name_plural = "Match Days"

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Team Name")
    coach = models.CharField(max_length=100, verbose_name="Coach Name")
    logo = models.ImageField(upload_to="team_logos/", blank=True, null=True, verbose_name="Team Logo")

    def __str__(self):
        return self.name

    # Ordenar los equipos por nombre
    class Meta:
        ordering = ['name']
        verbose_name = "Team"
        verbose_name_plural = "Teams" 

class Player(models.Model):
    POSITION_CHOICES = [
        ('GK', 'Arquero'),
        ('DF', 'Defensa'),
        ('MF', 'Mediocampista'),
        ('FW', 'Delantero'),
    ]

    name = models.CharField(max_length=100, verbose_name="Player Name")
    number = models.PositiveIntegerField(verbose_name="Jersey Number")
    position = models.CharField(max_length=2, choices=POSITION_CHOICES, verbose_name="Position")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players", verbose_name="Team")

    def __str__(self):
        return f"{self.name} ({self.team.name})"

class Match(models.Model):
    match_day = models.ForeignKey(MatchDay, on_delete=models.CASCADE, related_name='matches', null=True, blank=True, verbose_name="Match Day")
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    home_score = models.PositiveIntegerField(default=0, verbose_name="Home Team Score")
    away_score = models.PositiveIntegerField(default=0, verbose_name="Away Team Score")
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=[('scheduled', 'Scheduled'), ('finished', 'Finished')], default='scheduled')

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"

    @property
    def is_finished(self):
        return self.status == 'finished'
    
    def save(self, *args, **kwargs):
        # Si el match_day está asignado, usar su fecha automáticamente
        if self.match_day and not self.date:
            self.date = self.match_day.date
        super().save(*args, **kwargs)


class PointsAdjustment(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='points_adjustments')
    match = models.ForeignKey(Match, on_delete=models.SET_NULL, null=True, blank=True, related_name='points_adjustments')
    points = models.IntegerField(help_text="Puntos sumados o restados (puede ser negativo)")
    reason = models.CharField(max_length=255, help_text="Motivo del ajuste (ej: Observación, Sanción, etc.)")
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.team.name}: {self.points:+} ({self.reason})"