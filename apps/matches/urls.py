from django.urls import path

from apps.matches.views import home, match_detail_view, match_result_view, matches_view, statistics

urlpatterns = [
    path("", home, name="home"),
    path("partidos/", matches_view, name="matches"),
    path("partidos/<slug:match_slug>/", match_detail_view, name="match_detail"),
    path("partidos/<slug:match_slug>/resultado/", match_result_view, name="match_result"),
    path("goleadores/", statistics, name="statistics"),
]
