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
        # Pour la LISTE, on garde un format simple (compat)
        try:
            u = obj.owner if getattr(obj, "owner_id", None) else None
            return u.email if u else None
        except Exception:
            return None

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

    # Dans le détail, on renvoie 'coach' en OBJET complet
    coach = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    is_group_coach = serializers.SerializerMethodField()

    class Meta(GroupListSerializer.Meta):
        fields = GroupListSerializer.Meta.fields + [
            "members",
            "is_group_coach",
        ]
        read_only_fields = [
            "visibility", "join_policy",
            "coach", "members_count",
            "is_member", "is_owner_or_manager",
            "created_at",
        ]

    def _resolve_coach_user(self, obj):
        """
        Retourne l'utilisateur coach:
        - si champ coach_id/coac h existe -> obj.coach
        - sinon fallback sur owner
        """
        if hasattr(obj, "coach_id") and getattr(obj, "coach_id", None):
            try:
                return obj.coach
            except Exception:
                pass
        # fallback owner
        try:
            return obj.owner if getattr(obj, "owner_id", None) else None
        except Exception:
            return None

    def get_coach(self, obj):
        u = self._resolve_coach_user(obj)
        if not u:
            return None
        return {
            "id": u.id,
            "username": getattr(u, "username", None),
            "email": getattr(u, "email", None),
            # rôle global (table user)
            "role": getattr(u, "role", None),
            # optionnel: identité
            "first_name": getattr(u, "first_name", None),
            "last_name": getattr(u, "last_name", None),
        }

    def get_members(self, obj):
        rows = []

        # Inclure l'owner (avec user_role = rôle global)
        if getattr(obj, "owner_id", None) and getattr(obj, "owner", None):
            rows.append({
                "id": obj.owner_id,
                "username": obj.owner.username,
                "email": obj.owner.email,
                "first_name": obj.owner.first_name,
                "last_name": obj.owner.last_name,
                # rôle DANS le groupe (owner)
                "role": GroupMember.ROLE_OWNER,
                # rôle GLOBAL utilisateur
                "user_role": getattr(obj.owner, "role", None),
            })

        # Membres actifs
        qs = obj.memberships.select_related("user").filter(status=GroupMember.STATUS_ACTIVE)
        for gm in qs:
            if gm.user_id == getattr(obj, "owner_id", None):
                continue  # éviter doublon
            u = gm.user
            rows.append({
                "id": gm.user_id,
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                # rôle DANS le groupe (member/manager/owner...)
                "role": gm.role,
                # rôle GLOBAL utilisateur (admin/user/coach...)
                "user_role": getattr(u, "role", None),
            })
        return rows

    def get_is_group_coach(self, obj):
        """
        True ssi l'utilisateur courant est le coach de ce groupe COACH.
        - Si le modèle a un champ coach_id → on compare dessus
        - Sinon, fallback owner = coach
        """
        request = self.context.get("request")
        u = getattr(request, "user", None)
        if not u or not u.is_authenticated:
            return False

        # Doit être un groupe de type COACH
        if getattr(obj, "group_type", None) != Group.GroupType.COACH:
            return False

        coach_id = getattr(obj, "coach_id", None)
        if coach_id is not None:
            return u.id == coach_id

        # fallback : owner = coach
        return getattr(obj, "owner_id", None) == u.id


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
            # On expose aussi le rôle global ici (utile côté admin/coach)
            "role": getattr(u, "role", None),
        }
