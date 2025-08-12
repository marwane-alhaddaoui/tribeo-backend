from rest_framework import serializers
from apps.groups.models import Group, GroupMember

class GroupListSerializer(serializers.ModelSerializer):
    # compat: on continue d’exposer "coach" = owner.email
    coach = serializers.SerializerMethodField()
    members_count = serializers.IntegerField(read_only=True)
    is_member = serializers.SerializerMethodField()
    is_owner_or_manager = serializers.SerializerMethodField()
    sport_name = serializers.CharField(source="sport.name", read_only=True)

    class Meta:
        model = Group
        fields = [
            "id", "name", "description", "city",
            "sport", "sport_name",
            "visibility", "join_policy",
            "cover_image",
            "coach", "members_count",
            "is_member", "is_owner_or_manager",
            "created_at",
        ]
        read_only_fields = ["coach", "members_count", "is_member", "is_owner_or_manager", "created_at"]

    def get_coach(self, obj):
        return obj.owner.email if obj.owner_id else None

    def get_is_member(self, obj):
        u = self.context.get("request").user if self.context.get("request") else None
        if not u or not u.is_authenticated:
            return False
        if obj.owner_id == u.id:
            return True
        return GroupMember.objects.filter(group=obj, user=u, status=GroupMember.STATUS_ACTIVE).exists()

    def get_is_owner_or_manager(self, obj):
        u = self.context.get("request").user if self.context.get("request") else None
        if not u or not u.is_authenticated:
            return False
        if obj.owner_id == u.id:
            return True
        return GroupMember.objects.filter(
            group=obj, user=u,
            role__in=[GroupMember.ROLE_OWNER, GroupMember.ROLE_MANAGER],
            status=GroupMember.STATUS_ACTIVE
        ).exists()


class GroupDetailSerializer(GroupListSerializer):
    members = serializers.SerializerMethodField()

    class Meta(GroupListSerializer.Meta):
        fields = GroupListSerializer.Meta.fields + ["members"]

    def get_members(self, obj):
        # renvoie la liste des emails des membres actifs
        qs = GroupMember.objects.filter(group=obj, status=GroupMember.STATUS_ACTIVE).select_related("user")
        return [gm.user.email for gm in qs]


# Alias de compat pour les imports existants
GroupSerializer = GroupDetailSerializer
