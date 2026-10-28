import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0003_matchday_visibility"),
        ("teams", "0009_alter_player_number"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tournament",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Nombre del campeonato")),
                ("season", models.CharField(max_length=50, verbose_name="Temporada")),
                (
                    "category",
                    models.CharField(
                        choices=[("seniors", "Seniors"), ("super_seniors", "Super Seniors")],
                        default="seniors",
                        max_length=20,
                    ),
                ),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("setup", "Configuración"),
                            ("registration", "Inscripciones"),
                            ("in_progress", "En curso"),
                            ("completed", "Finalizado"),
                            ("suspended", "Suspendido"),
                        ],
                        default="setup",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Campeonato",
                "verbose_name_plural": "Campeonatos",
                "ordering": ["-season", "name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("name", "season", "category"),
                        name="unique_tournament_name_season_category",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="TournamentTeam",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tournament_memberships",
                        to="teams.team",
                    ),
                ),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="team_memberships",
                        to="tournaments.tournament",
                    ),
                ),
            ],
            options={
                "verbose_name": "Participación de equipo",
                "verbose_name_plural": "Participaciones de equipos",
                "ordering": ["team__name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("tournament", "team"),
                        name="unique_team_per_tournament",
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name="tournament",
            name="teams",
            field=models.ManyToManyField(
                blank=True,
                related_name="tournaments",
                through="tournaments.TournamentTeam",
                to="teams.team",
                verbose_name="Equipos participantes",
            ),
        ),
        migrations.AddField(
            model_name="matchday",
            name="tournament",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="matchdays",
                to="tournaments.tournament",
                verbose_name="Campeonato",
            ),
        ),
    ]
