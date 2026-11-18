from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playoffs", "0006_backfill_playoff_tournament"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="playoff",
            name="one_active_playoff_per_category",
        ),
        migrations.AddConstraint(
            model_name="playoff",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True, tournament__isnull=True),
                fields=("category",),
                name="one_active_legacy_playoff_per_category",
            ),
        ),
        migrations.AddConstraint(
            model_name="playoff",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True, tournament__isnull=False),
                fields=("tournament",),
                name="one_active_playoff_per_tournament",
            ),
        ),
    ]
