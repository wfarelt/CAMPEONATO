from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0003_manager_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="is_available_for_matchday",
            field=models.BooleanField(
                default=True,
                help_text="Determina si el equipo puede ser considerado para recomendaciones de partidos.",
                verbose_name="Disponible para jornada",
            ),
        ),
    ]
