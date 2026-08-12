from django.db import migrations


def seed_site_branding(apps, schema_editor):
	SiteBranding = apps.get_model("core", "SiteBranding")
	SiteBranding.objects.get_or_create(
		pk=1,
		defaults={
			"league_name": "Super Liga Nacional Florida",
			"primary_color": "#cc0000",
			"secondary_color": "#990000",
			"footer_location_name": "SANTA CRUZ DE LA SIERRA",
			"footer_organizer_name": "PROMO 2001T",
		},
	)


def unseed_site_branding(apps, schema_editor):
	SiteBranding = apps.get_model("core", "SiteBranding")
	SiteBranding.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

	dependencies = [
		("core", "0005_sitebranding"),
	]

	operations = [
		migrations.RunPython(seed_site_branding, unseed_site_branding),
	]