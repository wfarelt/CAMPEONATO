from django.db import migrations


def enable_team_manager_player_management(apps, schema_editor):
    AppConfiguration = apps.get_model("core", "AppConfiguration")
    AppConfiguration.objects.using(schema_editor.connection.alias).update_or_create(
        key="team_manager_enable_players",
        defaults={"is_enabled": True},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_alter_appconfiguration_key"),
    ]

    operations = [
        migrations.RunPython(enable_team_manager_player_management, migrations.RunPython.noop),
    ]