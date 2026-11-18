from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from apps.matches.models import Match, MatchEvent
from apps.payments.models import CardPayment
from apps.teams.models import Player, Team
from apps.tournaments.models import MatchDay, Tournament
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
