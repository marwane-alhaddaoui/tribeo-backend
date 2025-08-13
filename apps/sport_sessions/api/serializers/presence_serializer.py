from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.sport_sessions.models import SessionPresence
from .session_serializer import UserMiniSerializer

User = get_user_model()

class SessionPresenceSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user", queryset=User.objects.all(), write_only=True
    )

    class Meta:
        model = SessionPresence
        fields = ("user", "user_id", "present", "note", "marked_at", "marked_by")
        read_only_fields = ("marked_at", "marked_by")

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["marked_by"] = getattr(request, "user", None)
        obj, _ = SessionPresence.objects.update_or_create(
            session=self.context["session"],
            user=validated_data["user"],
            defaults={
                "present": validated_data.get("present", False),
                "note": validated_data.get("note", ""),
                "marked_by": validated_data.get("marked_by"),
            },
        )
        return obj
