from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_tournaments(apps, schema_editor):
    Playoff = apps.get_model("playoffs", "Playoff")
    PlayoffMatch = apps.get_model("playoffs", "PlayoffMatch")
    Tournament = apps.get_model("tournaments", "Tournament")
    database = schema_editor.connection.alias

    tournament_ids_by_playoff = {}
    links = PlayoffMatch.objects.using(database).filter(
        match__match_day__tournament__isnull=False,
    ).values_list("tie__playoff_id", "match__match_day__tournament_id")
    for playoff_id, tournament_id in links:
        tournament_ids_by_playoff.setdefault(playoff_id, set()).add(tournament_id)

    for playoff_id, tournament_ids in tournament_ids_by_playoff.items():
        if len(tournament_ids) != 1:
            continue
        tournament_id = next(iter(tournament_ids))
        playoff = Playoff.objects.using(database).filter(pk=playoff_id).first()
        tournament = Tournament.objects.using(database).filter(pk=tournament_id).first()
        if playoff and tournament and playoff.category == tournament.category:
            Playoff.objects.using(database).filter(pk=playoff_id).update(tournament_id=tournament_id)


def remove_legacy_tournament_links(apps, schema_editor):
    Playoff = apps.get_model("playoffs", "Playoff")
    database = schema_editor.connection.alias
    Playoff.objects.using(database).update(tournament=None)


class Migration(migrations.Migration):

    dependencies = [
        ("playoffs", "0005_playoff_tournament"),
        ("tournaments", "0005_backfill_legacy_tournaments"),
    ]

    operations = [
        migrations.RunPython(assign_legacy_tournaments, remove_legacy_tournament_links),
    ]
