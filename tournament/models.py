from django.db import models

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