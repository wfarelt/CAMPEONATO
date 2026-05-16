from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.choices import CHAMPIONSHIP_CATEGORY_CHOICES, PLAYER_POSITION_CHOICES
from apps.teams.models import Player, Team


TEAM_SEED_DATA = [
    ("Leones FC", "Carlos Mendoza"),
    ("Atletico Norte", "Luis Herrera"),
    ("Deportivo Sur", "Jorge Ramirez"),
    ("Real Union", "Miguel Torres"),
    ("Sporting Central", "Andres Rojas"),
    ("Academia Delta", "Rene Castillo"),
    ("Juventud Aurora", "Pablo Quispe"),
    ("Independiente 24", "Victor Salinas"),
    ("Nacional Andino", "Mario Aguilar"),
    ("Estrella Roja", "Fernando Varela"),
    ("Villa Olimpica", "Diego Cespedes"),
    ("San Martin", "Rodrigo Pacheco"),
]

FIRST_NAMES = [
    "Juan",
    "Pedro",
    "Diego",
    "Lucas",
    "Matias",
    "Sergio",
    "Pablo",
    "Cristian",
    "Adrian",
    "Ruben",
    "Nicolas",
    "Hector",
    "Leonel",
    "Ricardo",
    "Gabriel",
]

LAST_NAMES = [
    "Lopez",
    "Gonzales",
    "Fernandez",
    "Rojas",
    "Vargas",
    "Suarez",
    "Flores",
    "Mamani",
    "Romero",
    "Quiroga",
    "Salazar",
    "Castro",
    "Pena",
    "Ortiz",
    "Molina",
]


class Command(BaseCommand):
    help = "Carga 12 equipos base con sus jugadores de forma idempotente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            default="seniors",
            help="Categoria de los equipos (default: seniors)",
        )
        parser.add_argument(
            "--players-per-team",
            type=int,
            default=15,
            help="Cantidad de jugadores por equipo (default: 15)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        category = options["category"]
        players_per_team = options["players_per_team"]

        available_categories = {value for value, _ in CHAMPIONSHIP_CATEGORY_CHOICES}
        if category not in available_categories:
            raise CommandError(
                f"Categoria invalida: {category}. Usa una de: {', '.join(sorted(available_categories))}."
            )

        if players_per_team < 11:
            raise CommandError("players-per-team debe ser mayor o igual a 11.")

        valid_positions = [value for value, _ in PLAYER_POSITION_CHOICES]
        created_teams = 0
        created_players = 0
        updated_players = 0

        for team_index, (team_name, coach_name) in enumerate(TEAM_SEED_DATA, start=1):
            team, created = Team.objects.get_or_create(
                name=team_name,
                defaults={"coach": coach_name, "category": category},
            )

            if created:
                created_teams += 1
            else:
                changed = False
                if team.coach != coach_name:
                    team.coach = coach_name
                    changed = True
                if team.category != category:
                    team.category = category
                    changed = True
                if changed:
                    team.save(update_fields=["coach", "category"])

            for jersey_number in range(1, players_per_team + 1):
                first_name = FIRST_NAMES[(team_index + jersey_number) % len(FIRST_NAMES)]
                last_name = LAST_NAMES[(team_index * jersey_number) % len(LAST_NAMES)]
                player_name = f"{first_name} {last_name}"
                position = self._position_for_number(jersey_number, valid_positions)

                _, player_created = Player.objects.update_or_create(
                    team=team,
                    number=jersey_number,
                    defaults={
                        "name": player_name,
                        "position": position,
                    },
                )

                if player_created:
                    created_players += 1
                else:
                    updated_players += 1

        self.stdout.write(self.style.SUCCESS("Carga de equipos y jugadores completada."))
        self.stdout.write(f"Equipos creados: {created_teams}")
        self.stdout.write(f"Jugadores creados: {created_players}")
        self.stdout.write(f"Jugadores actualizados: {updated_players}")

    @staticmethod
    def _position_for_number(number, valid_positions):
        if number == 1:
            preferred = "GK"
        elif 2 <= number <= 5:
            preferred = "DF"
        elif 6 <= number <= 8:
            preferred = "MF"
        else:
            preferred = "FW"

        if preferred in valid_positions:
            return preferred
        return valid_positions[0]
