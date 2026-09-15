from django.db import migrations, models
import django.db.models.deletion


def migrate_legs_to_links(apps, schema_editor):
    PlayoffTie = apps.get_model("playoffs", "PlayoffTie")
    PlayoffMatch = apps.get_model("playoffs", "PlayoffMatch")
    for tie in PlayoffTie.objects.all().iterator():
        if tie.first_leg_id:
            PlayoffMatch.objects.create(tie_id=tie.pk, match_id=tie.first_leg_id, leg="first")
        if tie.second_leg_id:
            PlayoffMatch.objects.create(tie_id=tie.pk, match_id=tie.second_leg_id, leg="second")


class Migration(migrations.Migration):
    dependencies = [("playoffs", "0002_alter_playofftie_round")]

    operations = [
        migrations.AddField(
            model_name="leaguesettings",
            name="final_home_and_away",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaguesettings",
            name="sporting_advantage_on_tie",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaguesettings",
            name="replay_on_aggregate_tie",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="playofftie",
            name="next_slot",
            field=models.CharField(blank=True, max_length=4),
        ),
        migrations.AddField(
            model_name="playofftie",
            name="next_tie",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="previous_ties", to="playoffs.playofftie"),
        ),
        migrations.CreateModel(
            name="PlayoffMatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("leg", models.CharField(choices=[("single", "Partido unico"), ("first", "Ida"), ("second", "Vuelta"), ("replay", "Desempate")], default="single", max_length=10)),
                ("match", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="playoff_link", to="matches.match")),
                ("tie", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="match_links", to="playoffs.playofftie")),
            ],
        ),
        migrations.AddConstraint(
            model_name="playoffmatch",
            constraint=models.UniqueConstraint(fields=("tie", "leg"), name="unique_playoff_tie_leg"),
        ),
        migrations.AddIndex(
            model_name="playoffmatch",
            index=models.Index(fields=["tie", "leg"], name="playoffs_pl_tie_id_leg_7f0df0_idx"),
        ),
        migrations.RunPython(migrate_legs_to_links, migrations.RunPython.noop),
        migrations.RemoveField(model_name="playofftie", name="first_leg"),
        migrations.RemoveField(model_name="playofftie", name="second_leg"),
    ]