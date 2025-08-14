# apps/billing/services/quotas.py
from django.utils import timezone
from django.db import transaction
from apps.billing.models import UserMonthlyUsage, BillingProfile

# Limites par plan (adapte à ton besoin)
LIMITS = {
    BillingProfile.PLAN_FREE:     {"max_sessions": 2,   "max_groups": 1,   "max_participations": 5},
    BillingProfile.PLAN_PREMIUM:  {"max_sessions": 10,  "max_groups": 5,   "max_participations": 20},
    BillingProfile.PLAN_COACH:    {"max_sessions": 999, "max_groups": 999, "max_participations": 999},
}

def _ym(now=None) -> str:
    now = now or timezone.now()
    return now.strftime("%Y-%m")

def get_limits_for(user) -> dict:
    plan = getattr(getattr(user, "billing", None), "plan", BillingProfile.PLAN_FREE)
    return LIMITS.get(plan, LIMITS[BillingProfile.PLAN_FREE])

def usage_for(user, now=None) -> UserMonthlyUsage:
    ym = _ym(now)
    usage, _ = UserMonthlyUsage.objects.get_or_create(user=user, year_month=ym)
    return usage

@transaction.atomic
def increment_usage(user, *, sessions=0, groups=0, participations=0, now=None) -> UserMonthlyUsage:
    u = usage_for(user, now=now)
    if sessions:
        u.sessions_created = (u.sessions_created or 0) + sessions
    if groups:
        u.groups_created = (u.groups_created or 0) + groups
    if participations:
        u.participations = (u.participations or 0) + participations
    u.save()
    return u

def can_create_session(user) -> bool:
    limits = get_limits_for(user)
    u = usage_for(user)
    return u.sessions_created < limits["max_sessions"]

def can_create_group(user) -> bool:
    limits = get_limits_for(user)
    u = usage_for(user)
    return u.groups_created < limits["max_groups"]

def can_participate(user) -> bool:
    limits = get_limits_for(user)
    u = usage_for(user)
    return u.participations < limits["max_participations"]
