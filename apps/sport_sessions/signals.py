# apps/sport_sessions/signals.py

from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import SportSession

@receiver(pre_delete, sender=SportSession)
def clear_participants_before_delete(sender, instance, **kwargs):
    instance.participants.clear()
