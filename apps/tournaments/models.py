"""Tournaments domain models."""

from django.db import models

from apps.core.categories import CHAMPIONSHIP_CATEGORY_CHOICES, get_championship_label


class MatchDay(models.Model):
	category = models.CharField(
		max_length=20,
		choices=CHAMPIONSHIP_CATEGORY_CHOICES,
		default="seniors",
		verbose_name="Championship Category",
	)
	date = models.DateField(verbose_name="Match Day Date")
	description = models.TextField(blank=True, null=True, verbose_name="Description")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{get_championship_label(self.category)} - {self.date}"

	class Meta:
		ordering = ["-date"]
		constraints = [
			models.UniqueConstraint(fields=["category", "date"], name="unique_matchday_date_per_category"),
		]
		verbose_name = "Match Day"
		verbose_name_plural = "Match Days"
