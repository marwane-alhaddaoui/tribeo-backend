from django.utils import timezone
from django.conf import settings
from apps.billing.models import UserMonthlyUsage

def usage_for(user):
    today = timezone.now().date()
    obj, _ = UserMonthlyUsage.objects.get_or_create(
        user=user, year=today.year, month=today.month
    )
    return obj

def get_limits_for(user):
    plan = getattr(user, "plan", "FREE")
    return settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS["FREE"])
