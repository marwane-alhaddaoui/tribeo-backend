from rest_framework import serializers
from apps.billing.services.quotas import usage_for, get_limits_for

class QuotasSerializer(serializers.Serializer):
    plan = serializers.CharField()
    plan_expires_at = serializers.DateTimeField(allow_null=True)
    limits = serializers.DictField()
    usage = serializers.DictField()

    @classmethod
    def from_user(cls, user):
        limits = get_limits_for(user)
        usage = usage_for(user)
        return cls({
            "plan": user.plan,
            "plan_expires_at": user.plan_expires_at,
            "limits": limits,
            "usage": {
                "sessions_created": usage.sessions_created,
                "sessions_joined": usage.sessions_joined,
                "groups_joined": usage.groups_joined,
            }
        })
