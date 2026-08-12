from django.contrib import admin

from apps.core.models import AppConfiguration, SiteBranding, SocialLink


@admin.register(AppConfiguration)
class AppConfigurationAdmin(admin.ModelAdmin):
	list_display = ("key", "is_enabled", "updated_at")
	list_filter = ("is_enabled",)
	search_fields = ("key",)
	readonly_fields = ("created_at", "updated_at")


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
	list_display = ("label", "key", "url", "updated_at")
	search_fields = ("label", "url", "key")
	readonly_fields = ("created_at", "updated_at")


@admin.register(SiteBranding)
class SiteBrandingAdmin(admin.ModelAdmin):
	list_display = ("league_name", "primary_color", "secondary_color", "updated_at")
	fieldsets = (
		("Identidad", {"fields": ("league_name", "league_subtitle", "logo", "hero_bg_img")}),
		("Colores", {"fields": ("primary_color", "secondary_color")}),
		("Pie de página", {"fields": ("footer_location_name", "footer_organizer_name")}),
		("Fechas", {"fields": ("created_at", "updated_at")}),
	)
	readonly_fields = ("created_at", "updated_at")

	def has_add_permission(self, request):
		return not SiteBranding.objects.exists()

	def has_delete_permission(self, request, obj=None):
		return False
