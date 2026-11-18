from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("playoffs", "0008_playoff_settings_per_tournament"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="leaguesettings",
            options={
                "ordering": ["category", "tournament__season"],
                "verbose_name": "Configuracion de liga",
                "verbose_name_plural": "Configuraciones de liga",
            },
        ),
    ]
