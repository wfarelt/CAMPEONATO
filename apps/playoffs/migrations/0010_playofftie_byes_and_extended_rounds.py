from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playoffs", "0009_alter_leaguesettings_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="playofftie",
            name="is_bye",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="playofftie",
            name="round",
            field=models.CharField(
                choices=[
                    ("round_of_64", "Ronda de 64"),
                    ("round_of_32", "Ronda de 32"),
                    ("round_of_16", "Octavos de final"),
                    ("quarterfinal", "Cuartos de final"),
                    ("semifinal", "Semifinal"),
                    ("third_place", "Tercer puesto"),
                    ("final", "Final"),
                ],
                max_length=20,
            ),
        ),
    ]
