"""Models for playoff rules, brackets, and knockout ties."""

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.categories import get_championship_label
from apps.core.choices import CHAMPIONSHIP_CATEGORY_CHOICES


class LeagueSettings(models.Model):
    category = models.CharField(max_length=20, choices=CHAMPIONSHIP_CATEGORY_CHOICES, unique=True)
    teams_classified = models.PositiveIntegerField(default=8)
    playoffs_enabled = models.BooleanField(default=False)
    third_place_match = models.BooleanField(default=True)
    playoffs_home_and_away = models.BooleanField(default=False)
    penalties_on_aggregate_tie = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracion de liga"
        verbose_name_plural = "Configuraciones de liga"
        ordering = ["category"]

    def __str__(self):
        return get_championship_label(self.category)

    def clean(self):
        super().clean()
        if self.teams_classified < 2 or self.teams_classified & (self.teams_classified - 1):
            raise ValidationError({"teams_classified": "La cantidad de clasificados debe ser una potencia de dos mayor o igual a 2."})


class Playoff(models.Model):
    category = models.CharField(max_length=20, choices=CHAMPIONSHIP_CATEGORY_CHOICES)
    settings = models.ForeignKey(LeagueSettings, on_delete=models.PROTECT, related_name="playoffs")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Edicion de playoffs"
        verbose_name_plural = "Ediciones de playoffs"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["category"],
                condition=models.Q(is_active=True),
                name="one_active_playoff_per_category",
            ),
        ]

    def __str__(self):
        return f"Playoffs {get_championship_label(self.category)}"

    def clean(self):
        super().clean()
        if self.settings_id and self.settings.category != self.category:
            raise ValidationError({"settings": "La configuracion debe pertenecer a la misma categoria."})


class PlayoffTie(models.Model):
    ROUND_OF_16 = "round_of_16"
    QUARTERFINAL = "quarterfinal"
    SEMIFINAL = "semifinal"
    THIRD_PLACE = "third_place"
    FINAL = "final"
    ROUND_CHOICES = [
        (ROUND_OF_16, "Octavos de final"),
        (QUARTERFINAL, "Cuartos de final"),
        (SEMIFINAL, "Semifinal"),
        (THIRD_PLACE, "Tercer puesto"),
        (FINAL, "Final"),
    ]

    playoff = models.ForeignKey(Playoff, on_delete=models.CASCADE, related_name="ties")
    round = models.CharField(max_length=20, choices=ROUND_CHOICES)
    position = models.PositiveSmallIntegerField()
    home_team = models.ForeignKey("teams.Team", on_delete=models.PROTECT, related_name="playoff_home_ties", null=True, blank=True)
    away_team = models.ForeignKey("teams.Team", on_delete=models.PROTECT, related_name="playoff_away_ties", null=True, blank=True)
    first_leg = models.OneToOneField("matches.Match", on_delete=models.PROTECT, related_name="playoff_first_leg", null=True, blank=True)
    second_leg = models.OneToOneField("matches.Match", on_delete=models.PROTECT, related_name="playoff_second_leg", null=True, blank=True)
    winner = models.ForeignKey("teams.Team", on_delete=models.PROTECT, related_name="won_playoff_ties", null=True, blank=True)
    loser = models.ForeignKey("teams.Team", on_delete=models.PROTECT, related_name="lost_playoff_ties", null=True, blank=True)
    home_penalties = models.PositiveSmallIntegerField(null=True, blank=True)
    away_penalties = models.PositiveSmallIntegerField(null=True, blank=True)
    decided_by_penalties = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Llave de playoffs"
        verbose_name_plural = "Llaves de playoffs"
        ordering = ["round", "position"]
        constraints = [
            models.UniqueConstraint(fields=["playoff", "round", "position"], name="unique_playoff_tie_position"),
            models.CheckConstraint(
                condition=models.Q(home_team__isnull=True) | ~models.Q(home_team=models.F("away_team")),
                name="playoff_tie_teams_are_different",
            ),
        ]

    def __str__(self):
        return f"{self.get_round_display()} {self.position} - {self.playoff}"

    def clean(self):
        super().clean()
        team_ids = {self.home_team_id, self.away_team_id}
        if self.winner_id and self.winner_id not in team_ids:
            raise ValidationError({"winner": "El ganador debe participar en la llave."})
        if self.loser_id and self.loser_id not in team_ids:
            raise ValidationError({"loser": "El perdedor debe participar en la llave."})
        if self.winner_id and self.winner_id == self.loser_id:
            raise ValidationError({"loser": "Ganador y perdedor deben ser equipos distintos."})
        if self.decided_by_penalties:
            if self.home_penalties is None or self.away_penalties is None:
                raise ValidationError("Una definicion por penales requiere ambos marcadores.")
            if self.home_penalties == self.away_penalties:
                raise ValidationError("Los penales deben determinar un ganador.")