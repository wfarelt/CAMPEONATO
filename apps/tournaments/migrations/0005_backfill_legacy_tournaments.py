from django.db import migrations


CATEGORY_LABELS = {
    "seniors": "Seniors",
    "super_seniors": "Super Seniors",
}


def create_legacy_tournaments(apps, schema_editor):
    Tournament = apps.get_model("tournaments", "Tournament")
    TournamentTeam = apps.get_model("tournaments", "TournamentTeam")
    MatchDay = apps.get_model("tournaments", "MatchDay")
    Match = apps.get_model("matches", "Match")
    database = schema_editor.connection.alias

    category_years = {
        (category, match_date.year)
        for category, match_date in MatchDay.objects.using(database)
        .filter(tournament__isnull=True)
        .values_list("category", "date")
    }
    for category, year in category_years:
        tournament, _ = Tournament.objects.using(database).get_or_create(
            name=f"Campeonato {CATEGORY_LABELS[category]} {year}",
            season=str(year),
            category=category,
            defaults={"status": "setup"},
        )
        matchday_ids = list(
            MatchDay.objects.using(database)
            .filter(category=category, date__year=year, tournament__isnull=True)
            .values_list("pk", flat=True)
        )
        MatchDay.objects.using(database).filter(pk__in=matchday_ids).update(tournament_id=tournament.pk)

        team_ids = set()
        for home_team_id, away_team_id in Match.objects.using(database).filter(
            match_day_id__in=matchday_ids
        ).values_list("home_team_id", "away_team_id"):
            team_ids.update((home_team_id, away_team_id))
        TournamentTeam.objects.using(database).bulk_create(
            [TournamentTeam(tournament_id=tournament.pk, team_id=team_id) for team_id in team_ids],
            ignore_conflicts=True,
        )


def reverse_legacy_tournament_links(apps, schema_editor):
    Tournament = apps.get_model("tournaments", "Tournament")
    TournamentTeam = apps.get_model("tournaments", "TournamentTeam")
    MatchDay = apps.get_model("tournaments", "MatchDay")
    database = schema_editor.connection.alias
    legacy_ids = Tournament.objects.using(database).filter(name__startswith="Campeonato ").values_list(
        "pk", flat=True
    )
    MatchDay.objects.using(database).filter(tournament_id__in=legacy_ids).update(tournament=None)
    TournamentTeam.objects.using(database).filter(tournament_id__in=legacy_ids).delete()
    Tournament.objects.using(database).filter(pk__in=legacy_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0004_tournament_and_matchday_relation"),
        ("teams", "0009_alter_player_number"),
        ("matches", "0004_matchevent"),
    ]

    operations = [
        migrations.RunPython(create_legacy_tournaments, reverse_legacy_tournament_links),
    ]
