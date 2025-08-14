from copy import deepcopy
from django.conf import settings

# Normalise les clés attendues pour éviter les KeyError si un plan est partiel
_EXPECTED_KEYS = (
    "sessions_create_per_month",
    "sessions_join_per_month",
    "max_groups_joined",
    "can_create_groups",
)

def _normalize(plan_cfg: dict) -> dict:
    base = {k: None for k in _EXPECTED_KEYS}
    if not isinstance(plan_cfg, dict):
        return base
    out = deepcopy(base)
    out.update({k: plan_cfg.get(k) for k in _EXPECTED_KEYS})
    return out

def get_user_plan(user) -> str:
    """
    Détermine le plan à partir de l'utilisateur.
    Tu peux enrichir ici en lisant une table 'Subscription' Stripe, etc.
    """
    # Par défaut
    plan = "FREE"

    # Rôle → plan
    role = (getattr(user, "role", "") or "").upper()
    if role in ("PREMIUM", "COACH"):
        plan = role

    # TODO (si besoin): si user a un flag premium issu de billing, override plan = "PREMIUM"
    return plan

def get_limits_for(user) -> dict:
    plan = get_user_plan(user)
    plan_cfg = getattr(settings, "PLAN_LIMITS", {}).get(plan, {})
    return _normalize(plan_cfg)
