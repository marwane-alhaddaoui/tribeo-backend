from rest_framework import serializers

# ✅ IMPORTS MODELS
from apps.groups.models import (
    Group,
    GroupMember,
    GroupJoinRequest,
    GroupExternalMember,
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

    # 🔒 en lecture seule ici (la version détail rendra ce champ écrivable)
    group_type = serializers.CharField(read_only=True)
    visibility = serializers.SerializerMethodField()   # COMPAT
    join_policy = serializers.SerializerMethodField()  # COMPAT

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
    # ✍️ ici on rend le champ écrivable pour create/update
    group_type = serializers.ChoiceField(choices=Group.GroupType.choices, required=False)

    members = serializers.SerializerMethodField()
    # external_members = ExternalMemberSerializer(many=True, read_only=True)

    class Meta(GroupListSerializer.Meta):
        fields = GroupListSerializer.Meta.fields + ["members"]

    def get_members(self, obj):
        rows = []
        # Inclure l'owner
        if obj.owner_id and obj.owner:
            rows.append({
                "id": obj.owner_id,
                "username": obj.owner.username,
                "email": obj.owner.email,
                "first_name": obj.owner.first_name,
                "last_name": obj.owner.last_name,
                "role": GroupMember.ROLE_OWNER,
            })

        # Membres actifs
        qs = obj.memberships.select_related("user").filter(status=GroupMember.STATUS_ACTIVE)
        for gm in qs:
            if gm.user_id == obj.owner_id:
                continue  # éviter doublon
            rows.append({
                "id": gm.user_id,
                "username": gm.user.username,
                "email": gm.user.email,
                "first_name": gm.user.first_name,
                "last_name": gm.user.last_name,
                "role": gm.role,
            })
        return rows


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
