# apps/groups/api/views/group_crud_view.py
from django.db.models import Count, Q
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.groups.models import Group, GroupMember
from apps.groups.api.serializers.group_serializer import (
    GroupListSerializer, GroupDetailSerializer
)
from apps.groups.api.permissions.group_permissions import (
    IsGroupOwnerOrManager,  # ⬅️ on garde pour le détail
    # CanCreateGroup  # ⛔️ REMOVE: on ne l'utilise plus pour POST
)

from apps.billing.services.quotas import get_limits_for, usage_for, increment_usage

from apps.audit.utils import audit_log

class GroupListCreateView(generics.ListCreateAPIView):
    """
    GET: liste publique (OPEN + PRIVATE visibles) — lecture ouverte
    POST: création réservée aux utilisateurs authentifiés coach/premium (via policy+quotas)
    """
    authentication_classes = [JWTAuthentication]
    serializer_class = GroupDetailSerializer  # switch dans get_serializer_class

    def get_permissions(self):
        if self.request.method == "POST":
            # ⬇️ IMPORTANT: plus de permission custom ici (sinon 403)
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        u = self.request.user if self.request.user.is_authenticated else None
        qs = Group.objects.all().annotate(members_count=Count("memberships"))

        # Filtres optionnels
        sport_id = self.request.query_params.get("sport")
        if sport_id:
            qs = qs.filter(sport_id=sport_id)
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__icontains=city)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

        # Visibilité
        base = Q(group_type=Group.GroupType.OPEN) | Q(group_type=Group.GroupType.PRIVATE)
        if u:
            base |= Q(owner=u) | Q(memberships__user=u, memberships__status=GroupMember.STATUS_ACTIVE)
        return qs.filter(base).distinct()

    def get_serializer_class(self):
        return GroupListSerializer if self.request.method == "GET" else GroupDetailSerializer

    def _is_coach(self, user) -> bool:
        # Robust coach detection
        roles_rel = getattr(user, "roles", None)
        if roles_rel is not None:
            try:
                if roles_rel.filter(slug__iexact="COACH").exists():
                    return True
            except Exception:
                pass
        if getattr(user, "is_coach", False):
            return True
        return str(getattr(user, "role", "")).upper() == "COACH"

    def perform_create(self, serializer):
        user = self.request.user

        # --- Policy + quotas (renvoyer 400 via ValidationError) ---
        policy = getattr(settings, "GROUP_CREATION_POLICY", "ANY_MEMBER")
        limits = get_limits_for(user)
        u = usage_for(user)

        is_coach = self._is_coach(user)
        is_premium_like = limits.get("can_create_groups", False) is True

        if policy == "COACH_ONLY" and not is_coach:
            raise ValidationError({"detail": "Seuls les coachs peuvent créer des groupes."})
        if policy == "PREMIUM_ONLY" and not is_premium_like:
            raise ValidationError({"detail": "Ton plan ne permet pas de créer des groupes."})
        if policy == "COACH_OR_PREMIUM" and not (is_coach or is_premium_like):
            raise ValidationError({"detail": "Création réservée aux coachs ou aux comptes premium."})

        can_flag = limits.get("can_create_groups", None)
        if can_flag is False:
            raise ValidationError({"detail": "Ton plan ne permet pas de créer des groupes."})

        max_groups = limits.get("max_groups", None)  # None = illimité
        used = u.groups_created or 0
        if max_groups is not None and used >= int(max_groups):
            raise ValidationError({"detail": "Quota de groupes atteint pour ce mois."})

        # --- Save + owner devient membre ---
        group = serializer.save(owner=user)
        try:
            audit_log(self.request, "group.create", obj=group)
        except Exception:
            pass
        GroupMember.objects.get_or_create(
            group=group,
            user=user,
            defaults={"role": GroupMember.ROLE_OWNER, "status": GroupMember.STATUS_ACTIVE},
        )

        # --- Compteur ---
        try:
            increment_usage(user, groups=1)
        except Exception:
            pass


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: lecture ouverte (si groupe OPEN) ou accessible au membre/owner
    PATCH/PUT/DELETE: owner/manager authentifié uniquement
    """
    authentication_classes = [JWTAuthentication]
    serializer_class = GroupDetailSerializer

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsGroupOwnerOrManager()]

    def get_queryset(self):
        u = self.request.user if self.request.user.is_authenticated else None
        allowed = Q(group_type=Group.GroupType.OPEN)
        if u:
            allowed |= Q(owner=u) | Q(memberships__user=u, memberships__status=GroupMember.STATUS_ACTIVE)
        return Group.objects.filter(allowed).distinct()

    def perform_destroy(self, instance):
        is_owner = (instance.owner_id == getattr(self.request.user, "id", None))
        is_admin = getattr(self.request.user, "is_superuser", False) or getattr(self.request.user, "is_staff", False)
        if not (is_owner or is_admin):
            raise PermissionDenied("Only the group owner or an admin can delete this group.")
        instance.delete()
