from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Team Name")
    coach = models.CharField(max_length=100, verbose_name="Coach Name")
    logo = models.ImageField(upload_to="team_logos/", blank=True, null=True, verbose_name="Team Logo")

    def __str__(self):
        return self.name

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
