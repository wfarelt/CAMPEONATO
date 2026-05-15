from django.urls import path

from apps.matches.views import home, matches_view, statistics

urlpatterns = [
    path("", home, name="home"),
    path("matches/", matches_view, name="matches"),
    path("statistics/", statistics, name="statistics"),
]
