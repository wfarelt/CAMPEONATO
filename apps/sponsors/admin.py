from django.contrib import admin

from apps.sponsors.models import Sponsor


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
