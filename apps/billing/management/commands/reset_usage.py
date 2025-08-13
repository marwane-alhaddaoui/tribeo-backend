from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.billing.models import UserMonthlyUsage

class Command(BaseCommand):
    help = "Remet les compteurs du mois courant à 0 (debug seulement)"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        qs = UserMonthlyUsage.objects.filter(year=today.year, month=today.month)
        updated = qs.update(sessions_created=0, sessions_joined=0, groups_joined=0)
        self.stdout.write(self.style.SUCCESS(f"Réinitialisés: {updated}"))
