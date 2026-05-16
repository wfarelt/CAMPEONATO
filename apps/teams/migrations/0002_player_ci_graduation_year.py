from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="ci",
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name="CI"),
        ),
        migrations.AddField(
            model_name="player",
            name="graduation_year",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="Año de egreso"),
        ),
    ]
