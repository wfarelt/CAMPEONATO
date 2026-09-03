from django.urls import path

from apps.playoffs import views

urlpatterns = [
    path("playoffs/", views.playoffs_view, name="playoffs"),
    path("playoffs/generar/", views.generate_playoff_view, name="generate_playoff"),
]