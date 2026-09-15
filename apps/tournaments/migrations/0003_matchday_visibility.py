from django.db import migrations, models


def hide_return_legs(apps, schema_editor):
    MatchDay = apps.get_model("tournaments", "MatchDay")
    MatchDay.objects.filter(description__icontains="vuelta").update(is_visible=False)


class Migration(migrations.Migration):
    dependencies = [("tournaments", "0002_matchday_slug")]

    operations = [
        migrations.AddField(
            model_name="matchday",
            name="is_visible",
            field=models.BooleanField(default=True, verbose_name="Visible publicamente"),
        ),
        migrations.RunPython(hide_return_legs, migrations.RunPython.noop),
    ]