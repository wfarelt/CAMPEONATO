from apps.teams.models import Team


def get_all_teams(category=None):
    teams = Team.objects.all()
    if category:
        teams = teams.filter(category=category)
    return teams


def get_team_or_404(team_id, category=None):
    from django.shortcuts import get_object_or_404

    filters = {"pk": team_id}
    if category:
        filters["category"] = category
    return get_object_or_404(Team, **filters)


def build_team_api_data(team):
    return {
        "id": team.id,
        "name": team.name,
        "coach": team.coach,
        "category": team.category,
        "logo": team.logo.url if team.logo else None,
    }
