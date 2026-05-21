from django.urls import path

from apps.sponsors.views import (
    sponsor_create_view,
    sponsor_delete_view,
    sponsor_edit_view,
    sponsors_view,
)

urlpatterns = [
    path("auspiciadores/", sponsors_view, name="sponsors"),
    path("auspiciadores/crear/", sponsor_create_view, name="sponsor_create"),
    path("auspiciadores/<int:sponsor_id>/editar/", sponsor_edit_view, name="sponsor_edit"),
    path("auspiciadores/<int:sponsor_id>/eliminar/", sponsor_delete_view, name="sponsor_delete"),
]
