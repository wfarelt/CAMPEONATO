"""Tournaments domain models."""

from django.db import models
from django.utils.text import slugify

from apps.core.categories import CHAMPIONSHIP_CATEGORY_CHOICES, get_championship_label


class MatchDay(models.Model):
	category = models.CharField(
		max_length=20,
		choices=CHAMPIONSHIP_CATEGORY_CHOICES,
		default="seniors",
		verbose_name="Championship Category",
	)
	date = models.DateField(verbose_name="Match Day Date")
	slug = models.SlugField(max_length=180, unique=True, blank=True, null=True)
	description = models.TextField(blank=True, null=True, verbose_name="Description")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{get_championship_label(self.category)} - {self.date}"

	def _build_unique_slug(self):
		base_text = self.description or f"jornada-{self.date.strftime('%d-%m-%Y')}"
		base_slug = slugify(base_text)[:160] or "jornada"
		slug_candidate = base_slug
		counter = 2
		while MatchDay.objects.exclude(pk=self.pk).filter(slug=slug_candidate).exists():
			slug_candidate = f"{base_slug}-{counter}"[:180]
			counter += 1
		return slug_candidate

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = self._build_unique_slug()
		super().save(*args, **kwargs)

	class Meta:
		ordering = ["-date"]
		constraints = [
			models.UniqueConstraint(fields=["category", "date"], name="unique_matchday_date_per_category"),
		]
		verbose_name = "Match Day"
		verbose_name_plural = "Match Days"
