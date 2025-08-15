from rest_framework import serializers
from apps.billing.services.quotas import usage_for, get_limits_for
# ⬇️ Import du resolver interne
from apps.billing.services.quotas import _resolve_plan

class QuotasSerializer(serializers.Serializer):
    plan = serializers.CharField()
    plan_expires_at = serializers.DateTimeField(allow_null=True)
    limits = serializers.DictField()
    usage = serializers.DictField()

    @classmethod
    def from_user(cls, user):
        limits = get_limits_for(user)
        usage = usage_for(user)

        # ⚡ Plan résolu via BillingProfile/status + fallbacks
        resolved_plan = _resolve_plan(user)

        # Optionnel : plan_expires_at depuis BillingProfile si dispo
        plan_expires_at = getattr(user, "plan_expires_at", None)
        bp = getattr(user, "billing", None)
        if not plan_expires_at and bp:
            plan_expires_at = getattr(bp, "cancel_at", None) or getattr(bp, "current_period_end", None)

        return cls({
            "plan": resolved_plan,
            "plan_expires_at": plan_expires_at,
            "limits": limits,
            "usage": {
                "sessions_created": usage.sessions_created or 0,
                "participations":   usage.participations   or 0,
                "groups_created":   usage.groups_created   or 0,
                "trainings_created": getattr(usage, "trainings_created", 0) or 0,
            }
        })
