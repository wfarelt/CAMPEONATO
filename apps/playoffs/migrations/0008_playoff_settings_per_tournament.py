import django.db.models.deletion
from django.db import migrations, models


def copy_legacy_settings_to_tournaments(apps, schema_editor):
    LeagueSettings = apps.get_model("playoffs", "LeagueSettings")
    Playoff = apps.get_model("playoffs", "Playoff")
    Tournament = apps.get_model("tournaments", "Tournament")
    database = schema_editor.connection.alias
    setting_fields = [
        "teams_classified",
        "playoffs_enabled",
        "third_place_match",
        "playoffs_home_and_away",
        "final_home_and_away",
        "penalties_on_aggregate_tie",
        "sporting_advantage_on_tie",
        "replay_on_aggregate_tie",
    ]

    for tournament in Tournament.objects.using(database).all().iterator():
        legacy = LeagueSettings.objects.using(database).filter(
            category=tournament.category,
            tournament__isnull=True,
        ).first()
        values = {field: getattr(legacy, field) for field in setting_fields} if legacy else {}
        settings, _ = LeagueSettings.objects.using(database).get_or_create(
            tournament_id=tournament.pk,
            defaults={"category": tournament.category, **values},
        )
        Playoff.objects.using(database).filter(tournament_id=tournament.pk).update(settings_id=settings.pk)


def restore_legacy_settings(apps, schema_editor):
    LeagueSettings = apps.get_model("playoffs", "LeagueSettings")
    Playoff = apps.get_model("playoffs", "Playoff")
    database = schema_editor.connection.alias

    for playoff in Playoff.objects.using(database).filter(tournament__isnull=False).iterator():
        legacy = LeagueSettings.objects.using(database).filter(
            category=playoff.category,
            tournament__isnull=True,
        ).first()
        if legacy:
            Playoff.objects.using(database).filter(pk=playoff.pk).update(settings_id=legacy.pk)
    LeagueSettings.objects.using(database).filter(tournament__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("playoffs", "0007_active_playoff_per_tournament"),
        ("tournaments", "0008_assign_tournament_organizers"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaguesettings",
            name="tournament",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="playoff_settings",
                to="tournaments.tournament",
                verbose_name="Campeonato",
            ),
        ),
        migrations.AlterField(
            model_name="leaguesettings",
            name="category",
            field=models.CharField(
                choices=[("seniors", "Seniors"), ("super_seniors", "Super Seniors")],
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="leaguesettings",
            constraint=models.UniqueConstraint(
                condition=models.Q(tournament__isnull=True),
                fields=("category",),
                name="unique_legacy_playoff_settings_per_category",
            ),
        ),
        migrations.AddConstraint(
            model_name="leaguesettings",
            constraint=models.UniqueConstraint(
                condition=models.Q(tournament__isnull=False),
                fields=("tournament",),
                name="unique_playoff_settings_per_tournament",
            ),
        ),
        migrations.RunPython(copy_legacy_settings_to_tournaments, restore_legacy_settings),
    ]
