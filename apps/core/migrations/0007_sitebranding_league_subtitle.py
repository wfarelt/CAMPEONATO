from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		("core", "0006_seed_sitebranding"),
	]

	operations = [
		migrations.AddField(
			model_name="sitebranding",
			name="league_subtitle",
			field=models.CharField(default="NACIONAL FLORIDA", max_length=120),
		),
	]