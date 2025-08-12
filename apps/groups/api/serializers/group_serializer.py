# apps/groups/api/serializers/group_serializer.py
from rest_framework import serializers

# ✅ IMPORTS MODELS (inclut les nouveaux)
from apps.groups.models import (
    Group,
    GroupMember,
    GroupJoinRequest,
    GroupExternalMember,  # si tu n'utilises pas les membres externes, tu peux retirer cette ligne + le serializer associé
)

# ---- compat helpers (le front peut encore lire visibility/join_policy sans casser)
def compat_visibility_from_group_type(gt: str) -> str:
    return "PRIVATE" if gt == Group.GroupType.PRIVATE else "PUBLIC"

def compat_join_policy_from_group_type(gt: str) -> str:
    return "OPEN"


class GroupListSerializer(serializers.ModelSerializer):
    coach = serializers.SerializerMethodField()
    members_count = serializers.IntegerField(read_only=True)
    is_member = serializers.SerializerMethodField()
    is_owner_or_manager = serializers.SerializerMethodField()
    sport_name = serializers.CharField(source="sport.name", read_only=True)

    group_type = serializers.CharField(read_only=True)   # NEW
    visibility = serializers.SerializerMethodField()      # COMPAT
    join_policy = serializers.SerializerMethodField()     # COMPAT

    class Meta:
        model = Group
        fields = [
            "id", "name", "description", "city",
            "sport", "sport_name",
            "group_type",
            "visibility", "join_policy",
            "cover_image",
            "coach", "members_count",
            "is_member", "is_owner_or_manager",
            "created_at",
        ]
        read_only_fields = [
            "group_type", "visibility", "join_policy",
            "coach", "members_count",
            "is_member", "is_owner_or_manager",
            "created_at",
        ]

    def get_coach(self, obj):
        return obj.owner.email if obj.owner_id else None

    def _user(self):
        req = self.context.get("request")
        return getattr(req, "user", None) if req else None

    def get_is_member(self, obj):
        u = self._user()
        if not u or not u.is_authenticated:
            return False
        if obj.owner_id == u.id:
            return True
        return obj.memberships.filter(user=u, status=GroupMember.STATUS_ACTIVE).exists()

    def get_is_owner_or_manager(self, obj):
        u = self._user()
        if not u or not u.is_authenticated:
            return False
        if obj.owner_id == u.id:
            return True
        return obj.memberships.filter(
            user=u,
            role__in=[GroupMember.ROLE_OWNER, GroupMember.ROLE_MANAGER],
            status=GroupMember.STATUS_ACTIVE
        ).exists()

    def get_visibility(self, obj):
        return compat_visibility_from_group_type(obj.group_type)

    def get_join_policy(self, obj):
        return compat_join_policy_from_group_type(obj.group_type)


class GroupDetailSerializer(GroupListSerializer):
    members = serializers.SerializerMethodField()
    # 👉 si tu veux afficher les externes dans le détail, décommente la ligne suivante :
    # external_members = ExternalMemberSerializer(many=True, read_only=True)

    class Meta(GroupListSerializer.Meta):
        # 👉 si tu décommentes external_members au-dessus, ajoute "external_members" ci-dessous
        fields = GroupListSerializer.Meta.fields + ["members"]

    def get_members(self, obj):
        qs = obj.memberships.select_related("user").filter(status=GroupMember.STATUS_ACTIVE)
        return [gm.user.email for gm in qs]


# Alias de compat (si d'anciens imports l'utilisent)
GroupSerializer = GroupDetailSerializer


# ====== Nouveaux serializers ======

class ExternalMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupExternalMember
        fields = ["id", "first_name", "last_name", "note", "created_at"]
        read_only_fields = ["id", "created_at"]


class JoinRequestSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = GroupJoinRequest
        fields = ["id", "user", "status", "created_at"]

    def get_user(self, obj):
        u = obj.user
        return {
            "id": u.id,
            "username": u.username,
            "email": u.email,
        }
