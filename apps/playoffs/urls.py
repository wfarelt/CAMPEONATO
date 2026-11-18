from django.urls import path

from apps.playoffs import views

urlpatterns = [
    path("playoffs/", views.playoffs_view, name="playoffs"),
    path("playoffs/configuracion/", views.playoff_settings_view, name="playoff_settings"),
    path("playoffs/generar/", views.generate_playoff_view, name="generate_playoff"),
    path("playoffs/llave/<int:tie_id>/confirmar-cambio/", views.confirm_playoff_result_change_view, name="confirm_playoff_result_change"),
    path("playoffs/llave/<int:tie_id>/penales/", views.record_playoff_penalties_view, name="record_playoff_penalties"),
    path("playoffs/programar/<str:round_code>/", views.schedule_playoff_round_view, name="schedule_playoff_round"),
]