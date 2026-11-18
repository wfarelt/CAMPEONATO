from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0005_backfill_legacy_tournaments"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="matchday",
            name="unique_matchday_date_per_category",
        ),
        migrations.AddConstraint(
            model_name="matchday",
            constraint=models.UniqueConstraint(
                condition=models.Q(tournament__isnull=True),
                fields=("category", "date"),
                name="unique_legacy_matchday_date_per_category",
            ),
        ),
        migrations.AddConstraint(
            model_name="matchday",
            constraint=models.UniqueConstraint(
                condition=models.Q(tournament__isnull=False),
                fields=("tournament", "date"),
                name="unique_matchday_date_per_tournament",
            ),
        ),
    ]
