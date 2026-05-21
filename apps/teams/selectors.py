from apps.teams.models import Team


def get_all_teams(category=None):
    teams = Team.objects.all()
    if category:
        teams = teams.filter(category=category)
    return teams


def get_team_or_404(identifier, category=None):
    from django.shortcuts import get_object_or_404

    filters = {"slug": identifier}
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        filters = {"pk": int(identifier)}
    if category:
        filters["category"] = category
    return get_object_or_404(Team, **filters)


def build_team_api_data(team):
    return {
        "id": team.id,
        "slug": team.slug,
        "name": team.name,
        "coach": team.coach,
        "category": team.category,
        "is_available_for_matchday": team.is_available_for_matchday,
        "logo": team.logo.url if team.logo else None,
    }
