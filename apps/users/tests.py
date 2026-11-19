from django.contrib.auth import get_user_model
from django.core import mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.test import TestCase
from django.urls import reverse


class LoginTemplateTests(TestCase):
    def test_login_page_uses_bootstrap_form_and_links(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bootstrap@5.3.0/dist/css/bootstrap.min.css")
        self.assertContains(response, 'class="form-control login-control"')
        self.assertContains(response, 'class="btn btn-success w-100"')
        self.assertContains(response, reverse("password_reset"))
        self.assertContains(response, reverse("register"))
        self.assertNotContains(response, "cdn.tailwindcss.com")

    def test_login_page_displays_invalid_credentials_with_bootstrap_alert(self):
        response = self.client.post(
            reverse("login"),
            {"username": "missing-user", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="alert alert-danger"')
        self.assertContains(response, "Usuario o contraseña incorrectos.")


class RegisterTemplateTests(TestCase):
    def test_register_page_uses_bootstrap_controls(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bootstrap@5.3.0/dist/css/bootstrap.min.css")
        self.assertContains(response, 'class="form-control register-control"')
        self.assertContains(response, 'class="form-select register-control"')
        self.assertContains(response, 'class="btn btn-success w-100"')
        self.assertNotContains(response, "cdn.tailwindcss.com")

    def test_register_creates_and_authenticates_player_account(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "Alex",
                "last_name": "Jugador",
                "username": "alex-jugador",
                "email": "alex@example.com",
                "password1": "FutbolSeguro-2026!",
                "password2": "FutbolSeguro-2026!",
            },
        )

        self.assertRedirects(response, reverse("home"))
        user = get_user_model().objects.get(username="alex-jugador")
        self.assertEqual(user.role, "PLAYER")
        self.assertEqual(user.email, "alex@example.com")
        self.assertIn("_auth_user_id", self.client.session)


class PasswordResetTemplateTests(TestCase):
    def test_password_reset_page_uses_bootstrap_form(self):
        response = self.client.get(reverse("password_reset"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bootstrap@5.3.0/dist/css/bootstrap.min.css")
        self.assertContains(response, 'class="form-control reset-control"')
        self.assertContains(response, 'class="btn btn-success w-100"')
        self.assertContains(response, reverse("login"))
        self.assertNotContains(response, "cdn.tailwindcss.com")

    def test_password_reset_emails_registered_address(self):
        get_user_model().objects.create_user(
            username="reset-player",
            email="reset@example.com",
            password="FutbolSeguro-2026!",
        )

        response = self.client.post(reverse("password_reset"), {"email": "reset@example.com"})

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)


class PasswordResetStatusTemplateTests(TestCase):
    def test_password_reset_done_uses_bootstrap_and_keeps_generic_message(self):
        response = self.client.get(reverse("password_reset_done"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="status-card border rounded-3 p-4 p-sm-5 text-center"')
        self.assertContains(response, "Si existe una cuenta con ese correo")
        self.assertContains(response, 'class="btn btn-success w-100"')
        self.assertNotContains(response, "cdn.tailwindcss.com")


class PasswordResetConfirmTemplateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="confirm-reset-player",
            email="confirm-reset@example.com",
            password="OriginalPassword-2026!",
        )
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        self.url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})

    def test_password_reset_confirm_uses_bootstrap_fields(self):
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["validlink"])
        self.assertContains(response, "bootstrap@5.3.0/dist/css/bootstrap.min.css")
        self.assertContains(response, 'class="form-control confirm-control"')
        self.assertContains(response, 'class="btn btn-success w-100"')
        self.assertNotContains(response, "cdn.tailwindcss.com")

    def test_valid_reset_token_updates_password(self):
        reset_page = self.client.get(self.url, follow=True)
        self.assertTrue(reset_page.context["validlink"])

        response = self.client.post(
            reset_page.request["PATH_INFO"],
            {
                "new_password1": "NewSecurePassword-2026!",
                "new_password2": "NewSecurePassword-2026!",
            },
        )

        self.assertRedirects(response, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePassword-2026!"))

    def test_invalid_reset_token_shows_request_new_link_action(self):
        invalid_url = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": urlsafe_base64_encode(force_bytes(self.user.pk)), "token": "invalid-token"},
        )

        response = self.client.get(invalid_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["validlink"])
        self.assertContains(response, "Enlace inválido")
        self.assertContains(response, reverse("password_reset"))

    def test_password_reset_complete_links_to_login(self):
        response = self.client.get(reverse("password_reset_complete"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "¡Contraseña actualizada!")
        self.assertContains(response, reverse("login"))
        self.assertContains(response, 'class="btn btn-success w-100"')
        self.assertNotContains(response, "cdn.tailwindcss.com")