from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_existing_tournaments(apps, schema_editor):
    Tournament = apps.get_model("tournaments", "Tournament")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    database = schema_editor.connection.alias
    organizer_ids = list(
        User.objects.using(database).filter(role="ORGANIZER").values_list("pk", flat=True)
    )
    through = Tournament.organizers.through
    through.objects.using(database).bulk_create(
        [
            through(tournament_id=tournament_id, user_id=organizer_id)
            for tournament_id in Tournament.objects.using(database).values_list("pk", flat=True)
            for organizer_id in organizer_ids
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0006_matchday_uniqueness_per_tournament"),
        ("users", "0003_user_favorite_team"),
    ]

    operations = [
        migrations.AddField(
            model_name="tournament",
            name="organizers",
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={"role": "ORGANIZER"},
                related_name="organized_tournaments",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Organizadores autorizados",
            ),
        ),
        migrations.RunPython(assign_existing_tournaments, migrations.RunPython.noop),
    ]
