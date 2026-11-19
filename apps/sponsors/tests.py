from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.sponsors.models import Sponsor


class SponsorBootstrapTemplateTests(TestCase):
    def setUp(self):
        self.organizer = get_user_model().objects.create_user(
            username="sponsor-organizer",
            password="secret",
            role="ORGANIZER",
        )
        self.client.force_login(self.organizer)

    def test_sponsor_list_renders_bootstrap_grid(self):
        response = self.client.get(reverse("sponsors"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "row row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xl-4 g-3")
        self.assertContains(response, "No hay auspiciadores registrados.")

    def test_sponsor_form_renders_bootstrap_fields(self):
        response = self.client.get(reverse("sponsor_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "app-surface border rounded-3")
        self.assertContains(response, "class=\"form-control\"")
        self.assertContains(response, "class=\"form-check-input\"")

    def test_sponsor_delete_confirmation_renders_bootstrap_actions(self):
        sponsor = Sponsor.objects.create(name="Local Partner", image="sponsors/partner.png")

        response = self.client.get(reverse("sponsor_delete", kwargs={"sponsor_id": sponsor.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "app-surface border border-danger rounded-3")
        self.assertContains(response, "btn btn-danger")