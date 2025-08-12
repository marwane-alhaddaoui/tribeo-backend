from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.groups.models import Group, GroupMember

class IsGroupOwnerOrManager(BasePermission):
    """
    Autorise l'écriture si l'utilisateur est owner/manager actif du groupe.
    Lecture libre (on laisse la vue gérer public/privé).
    """
    def has_object_permission(self, request, view, obj: Group):
        # lecture: la vue décidera (public/privé), on ne bloque pas ici
        if request.method in SAFE_METHODS:
            return True
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if obj.owner_id == u.id:
            return True
        return GroupMember.objects.filter(
            group=obj, user=u, role__in=["owner","manager"], status="active"
        ).exists()


class IsGroupOwner(BasePermission):
    """ Pour DELETE (ou actions critiques): owner only. """
    def has_object_permission(self, request, view, obj: Group):
        if request.method in SAFE_METHODS:
            return True
        u = request.user
        return bool(u and u.is_authenticated and obj.owner_id == u.id)


class IsGroupActiveMember(BasePermission):
    """
    Lecture/accès réservés aux membres actifs d'un groupe (utile pour groupes privés
    ou pour /members). Laisse SAFE_METHODS aux membres actifs uniquement.
    """
    def has_object_permission(self, request, view, obj: Group):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if obj.owner_id == u.id:
            return True
        return GroupMember.objects.filter(group=obj, user=u, status="active").exists()
