from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0008_assign_tournament_organizers"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActiveChampionship",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="active_home_selections",
                        to="tournaments.tournament",
                    ),
                ),
            ],
            options={
                "verbose_name": "Campeonato activo del sitio",
                "verbose_name_plural": "Campeonato activo del sitio",
            },
        ),
    ]