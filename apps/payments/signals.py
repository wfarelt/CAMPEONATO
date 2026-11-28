from django.db import transaction
from django.db.models import F
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.payments.models import RegistrationAccount, RegistrationFee
from apps.tournaments.models import Tournament, TournamentTeam


def create_accounts(memberships, tournament_id, created_by=None):
    with transaction.atomic():
        Tournament.objects.filter(pk=tournament_id).update(id=F("id"))
        fee = RegistrationFee.objects.filter(tournament_id=tournament_id, is_active=True).first()
        if fee:
            RegistrationAccount.objects.bulk_create(
                [
                    RegistrationAccount(membership=membership, agreed_amount=fee.amount, created_by=created_by)
                    for membership in memberships
                ],
                ignore_conflicts=True,
            )


@receiver(post_save, sender=TournamentTeam)
def membership_created(sender, instance, created, **kwargs):
    if created:
        create_accounts([instance], instance.tournament_id)


@receiver(m2m_changed, sender=Tournament.teams.through)
def teams_added(sender, instance, action, reverse, pk_set, **kwargs):
    if action != "post_add" or not pk_set:
        return
    if reverse:
        for tournament_id in pk_set:
            create_accounts(TournamentTeam.objects.filter(tournament_id=tournament_id, team=instance), tournament_id)
    else:
        create_accounts(TournamentTeam.objects.filter(tournament=instance, team_id__in=pk_set), instance.pk)
