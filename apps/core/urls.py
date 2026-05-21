from django.urls import path

from apps.core.views import news_detail_view, search_view, settings_view

urlpatterns = [
    path("settings/", settings_view, name="settings"),
    path("search/", search_view, name="search"),
    path("noticias/<slug:news_slug>/", news_detail_view, name="news_detail"),
]
