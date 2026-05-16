from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.choices import CHAMPIONSHIP_CATEGORY_CHOICES, USER_ROLE_CHOICES


DEFAULT_USERS = [
    {
        "username": "admin",
        "email": "admin@campeonato.local",
        "role": "ADMIN",
        "is_staff": True,
        "is_superuser": True,
        "first_name": "Admin",
        "last_name": "Sistema",
    },
    {
        "username": "organizer",
        "email": "organizer@campeonato.local",
        "role": "ORGANIZER",
        "is_staff": True,
        "is_superuser": False,
        "first_name": "Usuario",
        "last_name": "Organizador",
    },
    {
        "username": "team_manager",
        "email": "team_manager@campeonato.local",
        "role": "TEAM_MANAGER",
        "is_staff": False,
        "is_superuser": False,
        "first_name": "Usuario",
        "last_name": "Equipo",
    },
    {
        "username": "referee",
        "email": "referee@campeonato.local",
        "role": "REFEREE",
        "is_staff": False,
        "is_superuser": False,
        "first_name": "Usuario",
        "last_name": "Arbitro",
    },
    {
        "username": "player",
        "email": "player@campeonato.local",
        "role": "PLAYER",
        "is_staff": False,
        "is_superuser": False,
        "first_name": "Usuario",
        "last_name": "Jugador",
    },
]


class Command(BaseCommand):
    help = "Crea roles (Groups), usuarios base y valida categorias del campeonato."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Admin123*",
            help="Password para usuarios nuevos (default: Admin123*)",
        )
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Si se indica, resetea password de usuarios existentes.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        reset_password = options["reset_password"]

        created_roles = 0
        for role_code, _ in USER_ROLE_CHOICES:
            _, created = Group.objects.get_or_create(name=role_code)
            if created:
                created_roles += 1

        user_model = get_user_model()
        created_users = 0
        updated_users = 0

        for user_data in DEFAULT_USERS:
            username = user_data["username"]
            role = user_data["role"]

            defaults = {
                "email": user_data["email"],
                "role": role,
                "is_staff": user_data["is_staff"],
                "is_superuser": user_data["is_superuser"],
                "is_active": True,
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
            }

            user, created = user_model.objects.get_or_create(username=username, defaults=defaults)

            if created:
                user.set_password(password)
                user.save()
                created_users += 1
            else:
                has_changes = False
                for field, value in defaults.items():
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        has_changes = True

                if reset_password:
                    user.set_password(password)
                    has_changes = True

                if has_changes:
                    user.save()
                    updated_users += 1

            role_group, _ = Group.objects.get_or_create(name=role)
            user.groups.set([role_group])

        categories = [value for value, _ in CHAMPIONSHIP_CATEGORY_CHOICES]

        self.stdout.write(self.style.SUCCESS("Datos iniciales procesados correctamente."))
        self.stdout.write(f"Roles creados: {created_roles}")
        self.stdout.write(f"Usuarios creados: {created_users}")
        self.stdout.write(f"Usuarios actualizados: {updated_users}")
        self.stdout.write(f"Categorias disponibles: {', '.join(categories)}")
