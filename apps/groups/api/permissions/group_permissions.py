from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.groups.models import Group, GroupMember

class CanCreateGroup(BasePermission):
    """Créer un groupe: coach ou premium uniquement."""
    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and (getattr(u, "is_coach", False) or getattr(u, "is_premium", False)))

class IsGroupOwnerOrManager(BasePermission):
    """
    Autorise l'écriture si l'utilisateur est owner/manager actif du groupe.
    Lecture libre (la vue filtre via get_queryset).
    """
    def has_object_permission(self, request, view, obj: Group):
        if request.method in SAFE_METHODS:
            return True
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if obj.owner_id == u.id:
            return True
        return obj.memberships.filter(
            user=u,
            role__in=[GroupMember.ROLE_OWNER, GroupMember.ROLE_MANAGER],
            status=GroupMember.STATUS_ACTIVE
        ).exists()

class IsGroupOwner(BasePermission):
    """Pour actions critiques: owner only."""
    def has_object_permission(self, request, view, obj: Group):
        if request.method in SAFE_METHODS:
            return True
        u = request.user
        return bool(u and u.is_authenticated and obj.owner_id == u.id)

class IsGroupActiveMember(BasePermission):
    """Lecture réservée aux membres actifs (ou owner)."""
    def has_object_permission(self, request, view, obj: Group):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if obj.owner_id == u.id:
            return True
        return obj.memberships.filter(user=u, status=GroupMember.STATUS_ACTIVE).exists()
