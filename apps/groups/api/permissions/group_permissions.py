# apps/groups/api/permissions/group_permissions.py
from typing import Any, Optional
from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.groups.models import Group, GroupMember

def _resolve_group(obj: Any) -> Optional[Group]:
    """
    Retourne l'objet Group quel que soit le type reçu :
    - si obj est déjà un Group -> le retourne
    - si obj possède un attribut .group -> retourne obj.group
    - sinon -> None
    """
    if isinstance(obj, Group):
        return obj
    if hasattr(obj, "group"):
        g = getattr(obj, "group", None)
        # Si c'est un RelatedManager (ex. obj.group.all()), on ignore
        return g if isinstance(g, Group) else None
    return None


class CanCreateGroup(BasePermission):
    """Créer un groupe: coach OU admin/staff/superuser."""
    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        u = getattr(request, "user", None)
        if not u or not u.is_authenticated:
            return False
        return (
            getattr(u, "is_coach", False) or          # ← propriété ajoutée ci-dessus
            getattr(u, "is_superuser", False) or
            getattr(u, "is_staff", False) or
            getattr(u, "role", "").lower() == "admin" # ceinture+bretelles si jamais
        )


class IsGroupOwnerOrManager(BasePermission):
    """
    Autorise l'écriture si l'utilisateur est owner/manager actif du groupe.
    Lecture libre (la vue filtre via get_queryset).
    Accepte un Group ou tout objet lié à un group via .group (ex: GroupExternalMember).
    """
    def has_object_permission(self, request, view, obj: Any):
        if request.method in SAFE_METHODS:
            return True

        u = request.user
        if not u or not u.is_authenticated:
            return False
        
        if getattr(u, "is_superuser", False) or getattr(u, "is_staff", False):
            return True

        g = _resolve_group(obj)
        if g is None:
            return False

        if g.owner_id == u.id:
            return True

        return g.memberships.filter(
            user=u,
            role__in=[GroupMember.ROLE_OWNER, GroupMember.ROLE_MANAGER],
            status=GroupMember.STATUS_ACTIVE,
        ).exists()


class IsGroupOwner(BasePermission):
    """Pour actions critiques: owner only. Accepte Group ou objet avec .group."""
    def has_object_permission(self, request, view, obj: Any):
        if request.method in SAFE_METHODS:
            return True

        u = request.user
        if not u or not u.is_authenticated:
            return False

        g = _resolve_group(obj)
        if g is None:
            return False

        return g.owner_id == u.id


class IsGroupActiveMember(BasePermission):
    """Lecture réservée aux membres actifs (ou owner). Accepte Group ou objet avec .group."""
    def has_object_permission(self, request, view, obj: Any):
        u = request.user
        if not u or not u.is_authenticated:
            return False

        g = _resolve_group(obj)
        if g is None:
            return False

        if g.owner_id == u.id:
            return True

        return g.memberships.filter(user=u, status=GroupMember.STATUS_ACTIVE).exists()
