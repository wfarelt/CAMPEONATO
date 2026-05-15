"""Write-side business logic for tournaments app."""


def save_matchday_with_matches(matchday_form, formset):
	"""Persist a matchday and its related matches from a bound formset."""
	matchday = matchday_form.save()

	instances = formset.save(commit=False)
	for instance in instances:
		instance.date = matchday.date
		instance.match_day = matchday
		instance.save()

	for obj in formset.deleted_objects:
		obj.delete()

	return matchday
