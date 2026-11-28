from datetime import date, time
from decimal import Decimal
from threading import Barrier, Thread
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import OperationalError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from apps.matches.models import Match, MatchEvent
from apps.payments.models import CardPayment, RegistrationAccount, RegistrationFeeHistory, RegistrationPayment
from apps.payments.services import configure_registration_fee, register_registration_payment, void_registration_payment
from apps.teams.models import Player, Team
from apps.tournaments.models import MatchDay, Tournament, TournamentTeam
from apps.users.models import User


class CardPaymentPermissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="payment-owner", password="secret", role="ORGANIZER")
        self.other_organizer = User.objects.create_user(
            username="payment-other",
            password="secret",
            role="ORGANIZER",
        )
        self.player_user = User.objects.create_user(username="payment-player", password="secret", role="PLAYER")
        self.team = Team.objects.create(name="Payment Team", coach="Coach", category="seniors")
        self.tournament = Tournament.objects.create(name="Payment League", season="2026", category="seniors")
        self.tournament.organizers.add(self.owner)
        self.tournament.teams.add(self.team)
        matchday = MatchDay.objects.create(
            tournament=self.tournament,
            category="seniors",
            date=date(2026, 6, 1),
        )
        self.match = Match.objects.create(
            match_day=matchday,
            home_team=self.team,
            away_team=Team.objects.create(name="Opponent", coach="Coach", category="seniors"),
            date=matchday.date,
            time=time(15, 0),
            status="finished",
        )
        player = Player.objects.create(team=self.team, name="Player One", position="DF")
        self.event = MatchEvent.objects.create(
            match=self.match,
            player=player,
            team=self.team,
            event_type=MatchEvent.YELLOW_CARD,
        )
        self.url = reverse("register_card_payment", args=[self.event.pk])

    def test_owner_sees_bootstrap_card_payment_form(self):
        self.client.force_login(self.owner)

        response = self.client.get(f"{self.url}?category=seniors&tournament={self.tournament.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="app-surface border rounded-3 p-3 p-md-4"')
        self.assertContains(response, 'class="form-control bg-dark text-white border-secondary"')
        self.assertContains(response, 'class="form-check-input"')
        self.assertContains(response, "Player One")
        self.assertContains(response, "Marcar como pagado")

    def test_owner_sees_bootstrap_card_payment_list(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("card_payments"),
            {"category": "seniors", "tournament": self.tournament.pk, "filtro": "pendientes"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Filtrar pagos"')
        self.assertContains(response, 'class="table app-table table-hover align-middle mb-0"')
        self.assertContains(response, "Player One")
        self.assertContains(response, "Pendiente")
        self.assertContains(response, "Registrar")

    def test_owner_can_register_card_payment(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            f"{self.url}?category=seniors&tournament={self.tournament.pk}",
            {"amount": "25.00", "paid": "on", "paid_date": "2026-06-02", "notes": "Pagado"},
        )

        self.assertRedirects(
            response,
            f"{reverse('card_payments')}?category=seniors",
            fetch_redirect_response=False,
        )
        payment = CardPayment.objects.get(match_event=self.event)
        self.assertEqual(payment.amount, 25)
        self.assertTrue(payment.paid)

    def test_other_organizer_cannot_register_payment_and_no_row_is_created(self):
        self.client.force_login(self.other_organizer)

        response = self.client.post(
            f"{self.url}?category=seniors&tournament={self.tournament.pk}",
            {"amount": "25.00", "paid": "on", "paid_date": "2026-06-02", "notes": ""},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(CardPayment.objects.filter(match_event=self.event).exists())

    def test_player_cannot_register_payment_and_get_does_not_create_payment(self):
        self.client.force_login(self.player_user)

        get_response = self.client.get(self.url, {"category": "seniors"})

        self.assertEqual(get_response.status_code, 403)
        self.assertFalse(CardPayment.objects.filter(match_event=self.event).exists())
        post_response = self.client.post(
            f"{self.url}?category=seniors",
            {"amount": "25.00", "paid": "on", "paid_date": "2026-06-02", "notes": ""},
        )
        self.assertEqual(post_response.status_code, 403)
        self.assertFalse(CardPayment.objects.filter(match_event=self.event).exists())

    def test_other_organizer_cannot_view_or_edit_card_payment(self):
        self.client.force_login(self.other_organizer)

        response = self.client.get(f"{self.url}?category=seniors")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(CardPayment.objects.filter(match_event=self.event).exists())


class RegistrationPaymentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="fee-owner", password="secret", role="ORGANIZER")
        self.other = User.objects.create_user(username="fee-other", password="secret", role="ORGANIZER")
        self.player = User.objects.create_user(username="fee-player", password="secret", role="PLAYER")
        self.tournament = Tournament.objects.create(name="Fee League", season="2026", category="seniors")
        self.tournament.organizers.add(self.owner)
        self.team = Team.objects.create(name="Fee Team", coach="Coach", category="seniors")
        self.opponent = Team.objects.create(name="Fee Opponent", coach="Coach", category="seniors")
        self.tournament.teams.add(self.team)
        self.membership = TournamentTeam.objects.get(tournament=self.tournament, team=self.team)

    def configure(self, amount="500.00", active=True):
        configure_registration_fee(self.tournament, self.owner, Decimal(amount), "", active)

    def payment_data(self, amount="200.00", submission_id=None):
        return {
            "payment_date": date(2026, 11, 1), "amount": Decimal(amount), "method": "cash",
            "receipt_number": "", "notes": "", "submission_id": submission_id or uuid4(),
        }

    def test_existing_and_new_memberships_capture_fee_without_repricing(self):
        self.assertFalse(RegistrationAccount.objects.exists())
        self.configure()
        account = RegistrationAccount.objects.get(membership=self.membership)
        self.assertEqual(account.created_by, self.owner)
        self.configure("600.00")
        self.tournament.teams.add(self.opponent)
        self.assertEqual(account.agreed_amount, Decimal("500"))
        self.assertEqual(RegistrationAccount.objects.get(membership__team=self.opponent).agreed_amount, Decimal("600"))
        self.assertEqual(RegistrationFeeHistory.objects.count(), 2)

    def test_inactive_fee_defers_new_account_until_activation(self):
        self.configure("500", active=False)
        self.assertFalse(RegistrationAccount.objects.exists())
        self.configure("600")
        self.assertEqual(RegistrationAccount.objects.get(membership=self.membership).agreed_amount, Decimal("600"))

    def test_partial_full_duplicate_and_void_payments(self):
        self.configure()
        account = RegistrationAccount.objects.get(membership=self.membership)
        data = self.payment_data()
        payment = register_registration_payment(account, self.owner, data)
        self.assertEqual(account.payment_status, "PARCIAL")
        self.assertEqual(account.balance, Decimal("300"))
        self.assertEqual(register_registration_payment(account, self.owner, data).pk, payment.pk)
        self.assertEqual(account.payments.count(), 1)
        with self.assertRaises(ValidationError):
            register_registration_payment(account, self.owner, self.payment_data("301"))
        final = register_registration_payment(account, self.owner, self.payment_data("300"))
        self.assertEqual(account.payment_status, "PAGADO")
        self.assertEqual(account.percentage_paid, Decimal("100"))
        with self.assertRaises(ValidationError):
            void_registration_payment(final, self.owner, " ")
        void_registration_payment(final, self.owner, "Error de comprobante")
        final.refresh_from_db()
        self.assertEqual(final.voided_by, self.owner)
        self.assertEqual(account.balance, Decimal("300"))
        self.assertEqual(account.payment_status, "PARCIAL")
        with self.assertRaises(ValidationError):
            void_registration_payment(final, self.owner, "Repetido")

    def test_invalid_payments_and_tampered_idempotency_key(self):
        self.configure()
        account = RegistrationAccount.objects.get(membership=self.membership)
        for amount in ("0", "-1"):
            with self.assertRaises(ValidationError):
                register_registration_payment(account, self.owner, self.payment_data(amount))
        data = self.payment_data()
        register_registration_payment(account, self.owner, data)
        with self.assertRaises(ValidationError):
            register_registration_payment(account, self.owner, {**data, "amount": Decimal("100")})
        self.assertEqual(account.payments.count(), 1)

    def test_prefetched_account_does_not_allow_stale_balance(self):
        self.configure()
        account = RegistrationAccount.objects.prefetch_related("payments").get(membership=self.membership)
        register_registration_payment(account, self.owner, self.payment_data("400"))
        with self.assertRaises(ValidationError):
            register_registration_payment(account, self.owner, self.payment_data("200"))
        self.assertEqual(RegistrationPayment.objects.filter(account=account).count(), 1)

    def test_membership_with_voided_payment_cannot_be_removed(self):
        self.configure()
        account = RegistrationAccount.objects.get(membership=self.membership)
        payment = register_registration_payment(account, self.owner, self.payment_data())
        void_registration_payment(payment, self.owner, "Anulado")
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.tournament.teams.remove(self.team)
        self.assertTrue(TournamentTeam.objects.filter(pk=self.membership.pk).exists())
        with self.assertRaises(ValidationError):
            payment.delete()
        with self.assertRaises(ValidationError):
            RegistrationPayment.objects.filter(pk=payment.pk).delete()

        self.client.force_login(self.owner)
        url = reverse("team_delete", args=[self.team.slug]) + f"?category=seniors&tournament={self.tournament.pk}"
        response = self.client.post(url)
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "historial de pagos", status_code=409)

    def test_tournament_edit_records_new_account_creator_and_blocks_paid_removal(self):
        self.configure()
        self.client.force_login(self.owner)
        url = reverse("tournament_edit", args=[self.tournament.pk]) + "?category=seniors"
        payload = {
            "name": self.tournament.name, "season": self.tournament.season,
            "category": self.tournament.category, "status": self.tournament.status,
            "teams": [str(self.team.pk), str(self.opponent.pk)],
        }
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        opponent_account = RegistrationAccount.objects.get(membership__team=self.opponent)
        self.assertEqual(opponent_account.created_by, self.owner)
        account = RegistrationAccount.objects.get(membership=self.membership)
        register_registration_payment(account, self.owner, self.payment_data())
        payload["teams"] = [str(self.opponent.pk)]
        payload["name"] = "No debe guardarse"
        response = self.client.post(url, payload)
        self.assertContains(response, "historial de pagos")
        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.name, "Fee League")
        self.assertTrue(self.tournament.teams.filter(pk=self.team.pk).exists())

    def test_authorization_and_payment_post(self):
        self.configure()
        account = RegistrationAccount.objects.get(membership=self.membership)
        payment_url = reverse("registration_payment", args=[account.pk])
        payload = {"payment_date": "2026-11-01", "amount": "200.00", "method": "cash",
                   "receipt_number": "", "notes": "", "submission_id": str(uuid4())}
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(payment_url, payload).status_code, 403)
        self.assertEqual(self.client.get(reverse("registration_fee", args=[self.tournament.pk])).status_code, 403)
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(reverse("registration_account", args=[account.pk])).status_code, 403)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("registration_account", args=[account.pk])).status_code, 200)
        self.assertEqual(self.client.post(payment_url, payload).status_code, 302)
        self.assertEqual(self.client.post(payment_url, payload).status_code, 302)
        self.assertEqual(RegistrationPayment.objects.count(), 1)
        self.assertContains(self.client.get(reverse("registration_account", args=[account.pk])), "PARCIAL")
        self.assertContains(self.client.get(reverse("registration_accounts"), {"tournament": self.tournament.pk}), "Fee Team")

    def test_match_sheet_only_discloses_authorized_tournament_balances(self):
        self.tournament.teams.add(self.opponent)
        self.configure()
        account = RegistrationAccount.objects.get(membership=self.membership)
        register_registration_payment(account, self.owner, self.payment_data())
        matchday = MatchDay.objects.create(tournament=self.tournament, category="seniors", date=date(2026, 11, 1))
        match = Match.objects.create(match_day=matchday, home_team=self.team, away_team=self.opponent,
                                     date=matchday.date, time=time(15, 0))
        url = reverse("match_detail", args=[match.slug]) + f"?category=seniors&tournament={self.tournament.pk}"
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertContains(response, "Pagado: Bs 200,00")
        self.assertContains(response, "PARCIAL")
        summary_url = reverse("match_registration_summary", args=[match.slug])
        summary = self.client.get(summary_url).json()
        self.assertEqual(Decimal(summary["home"]["balance"]), Decimal("300"))
        register_registration_payment(account, self.owner, self.payment_data("100"))
        summary = self.client.get(summary_url).json()
        self.assertEqual(Decimal(summary["home"]["balance"]), Decimal("200"))
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(url), "Pagado: Bs")
        self.assertEqual(self.client.get(summary_url).status_code, 403)
        self.client.force_login(self.player)
        self.assertNotContains(self.client.get(url), "Pagado: Bs")
        self.assertEqual(self.client.get(summary_url).status_code, 403)

    def test_fee_and_notes_history_are_audited_through_views(self):
        self.client.force_login(self.owner)
        url = reverse("registration_fee", args=[self.tournament.pk])
        self.assertEqual(self.client.post(url, {"amount": "500", "notes": "Inicial", "is_active": "on"}).status_code, 302)
        self.assertContains(self.client.get(url), "Inicial")
        account = RegistrationAccount.objects.get(membership=self.membership)
        notes_url = reverse("registration_account_notes", args=[account.pk])
        self.client.post(notes_url, {"notes": "Primera observación"})
        self.client.post(notes_url, {"notes": "Segunda observación"})
        self.assertEqual(account.note_history.count(), 2)
        self.assertTrue(account.note_history.filter(created_by=self.owner, notes="Primera observación").exists())

    def test_free_registration_is_paid_without_division_by_zero(self):
        self.configure("0")
        account = RegistrationAccount.objects.get(membership=self.membership)
        self.assertEqual(account.payment_status, "PAGADO")
        self.assertEqual(account.percentage_paid, 100)


class RegistrationConcurrencyTests(TransactionTestCase):
    def test_simultaneous_payments_cannot_exceed_balance(self):
        admin = User.objects.create_superuser(username="concurrent-admin", password="secret")
        tournament = Tournament.objects.create(name="Concurrent", season="2026", category="seniors")
        team = Team.objects.create(name="Concurrent Team", coach="Coach", category="seniors")
        tournament.teams.add(team)
        configure_registration_fee(tournament, admin, Decimal("500"), "", True)
        account = RegistrationAccount.objects.select_related("membership__tournament").get(membership__team=team)
        barrier = Barrier(2)
        results = []

        def pay():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                register_registration_payment(account, admin, {
                    "payment_date": date(2026, 11, 1), "amount": Decimal("400"), "method": "cash",
                    "receipt_number": "", "notes": "", "submission_id": uuid4(),
                })
                results.append("paid")
            except ValidationError:
                results.append("rejected")
            except OperationalError as error:
                results.append("locked" if "locked" in str(error).lower() else str(error))
            finally:
                close_old_connections()

        threads = [Thread(target=pay), Thread(target=pay)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(results.count("paid"), 1, results)
        self.assertEqual(len(results), 2)
        self.assertTrue(any(result in {"rejected", "locked"} for result in results), results)
        self.assertEqual(RegistrationPayment.objects.filter(account=account).count(), 1)
        self.assertEqual(RegistrationAccount.objects.get(pk=account.pk).balance, Decimal("100"))
