# apps/billing/services/quotas.py
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from typing import Optional, Dict, Any

from apps.billing.models import UserMonthlyUsage, BillingProfile

# -----------------------
# Helpers internes
# -----------------------

def _ym(now=None) -> str:
    now = now or timezone.now()
    return now.strftime("%Y-%m")

def _raw_limits_from_settings(plan: str) -> Dict[str, Any]:
    """
    Récupère les limites brutes depuis settings.PLAN_LIMITS selon le plan fourni.
    Si non trouvé, tente un fallback sur FREE, sinon {}.
    """
    try:
        data = getattr(settings, "PLAN_LIMITS", {})
        if not isinstance(data, dict):
            return {}
        if plan in data:
            return data[plan] or {}
        if BillingProfile.PLAN_FREE in data:
            return data[BillingProfile.PLAN_FREE] or {}
        return {}
    except Exception:
        return {}

def _first_present(d: Dict[str, Any], *keys, default=None):
    """Retourne la première valeur non-None trouvée dans d pour une liste de clés."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def _normalize_limits(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sessions_create_per_month": _first_present(raw, "sessions_create_per_month", "max_sessions", default=None),
        "sessions_join_per_month":   _first_present(raw, "sessions_join_per_month",   "max_participations", default=None),
        "max_groups":                _first_present(raw, "max_groups", "max_groups_joined", default=None),
        "can_create_groups":         _first_present(raw, "can_create_groups", default=None),

        # NEW coach-specific:
        "trainings_create_per_month": _first_present(raw, "trainings_create_per_month", default=None),
        "can_create_trainings":       _first_present(raw, "can_create_trainings",       default=False),
    }


def can_create_training(user) -> bool:
    limits = get_limits_for(user)
    if limits.get("can_create_trainings") is False:
        return False
    u = usage_for(user)
    limit = limits.get("trainings_create_per_month", 0)
    # Si tu ajoutes un champ trainings_created dans le modèle, remplace 0 par u.trainings_created
    used = getattr(u, "trainings_created", 0)
    return True if limit is None else (used < int(limit))


def _resolve_plan(user) -> str:
    """
    Résout le plan de l'utilisateur de façon robuste :
      1) BillingProfile.plan si présent ET status == 'active'
      2) fallbacks: user.plan / user.account_type / user.role
      3) staff/superuser => PREMIUM (bypass pratique)
      4) défaut: FREE
    Normalise toujours en UPPERCASE.
    """
    # Bypass staff/superuser (choix: PREMIUM illimité dans settings.PLAN_LIMITS)
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return "PREMIUM"

    # Source Stripe (BillingProfile)
    bp = getattr(user, "billing", None)
    bp_plan = getattr(bp, "plan", None)
    bp_status = getattr(bp, "status", None)
    if bp_plan:
        # n'accepter le plan billing que si la souscription est active
        if not bp_status or str(bp_status).lower() != "active":
            return "FREE"
        return str(bp_plan).upper()

    # Fallbacks sur des champs du user
    raw_plan = (
        getattr(user, "plan", None)
        or getattr(user, "account_type", None)
        or getattr(user, "role", None)
        or "FREE"
    )
    return str(raw_plan).upper()

# -----------------------
# API publique du service
# -----------------------

def get_limits_for(user) -> dict:
    """
    Détermine le plan via _resolve_plan, puis mappe settings.PLAN_LIMITS
    vers un dictionnaire normalisé (cf _normalize_limits).
    """
    plan = _resolve_plan(user)
    raw = _raw_limits_from_settings(plan)
    return _normalize_limits(raw)

def usage_for(user, now=None) -> UserMonthlyUsage:
    ym = _ym(now)
    usage, _ = UserMonthlyUsage.objects.get_or_create(user=user, year_month=ym)
    return usage

@transaction.atomic
def increment_usage(user, *, sessions=0, groups=0, participations=0, trainings=0, now=None) -> UserMonthlyUsage:    
    """
    Incrémente les compteurs réels stockés en base. Ces noms DOIVENT
    correspondre aux champs du modèle UserMonthlyUsage.
    """
    u = usage_for(user, now=now)
    if sessions:
        u.sessions_created = (u.sessions_created or 0) + sessions
    if groups:
        u.groups_created = (u.groups_created or 0) + groups
    if participations:
        u.participations = (u.participations or 0) + participations
    if trainings:
        u.trainings_created = (u.trainings_created or 0) + trainings
    u.save()
    return u

# ------- Règles booléennes (utilisent les limites normalisées) -------

def _lt_or_unlimited(used: int, limit: Optional[int]) -> bool:
    """True si illimité (None) ou si used < limit."""
    return True if limit is None else (used < int(limit))

def can_create_session(user) -> bool:
    # Bypass explicite pour staff/superuser (double filet de sécurité)
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    limits = get_limits_for(user)
    u = usage_for(user)
    limit = limits.get("sessions_create_per_month", None)
    return _lt_or_unlimited(u.sessions_created or 0, limit)

def can_create_group(user) -> bool:
    limits = get_limits_for(user)
    # Si un flag explicitement False existe, on le respecte.
    can_flag = limits.get("can_create_groups", None)
    if can_flag is False:
        return False
    u = usage_for(user)
    limit = limits.get("max_groups", None)
    return _lt_or_unlimited(u.groups_created or 0, limit)

def can_participate(user) -> bool:
    limits = get_limits_for(user)
    u = usage_for(user)
    limit = limits.get("sessions_join_per_month", None)
    return _lt_or_unlimited(u.participations or 0, limit)
