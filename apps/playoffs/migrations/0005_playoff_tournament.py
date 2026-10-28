import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playoffs", "0004_alter_playoff_options_and_more"),
        ("tournaments", "0004_tournament_and_matchday_relation"),
    ]

    operations = [
        migrations.AddField(
            model_name="playoff",
            name="tournament",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="playoffs",
                to="tournaments.tournament",
                verbose_name="Campeonato",
            ),
        ),
    ]
