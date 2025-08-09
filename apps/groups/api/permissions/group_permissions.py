# apps/groups/api/permissions/group_permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsCoachOrAdmin(BasePermission):
    """
    Autorise lecture à tous, écriture/édition seulement au coach du groupe ou à un admin.
    Compatible avec des vues DRF 'object-level' (Retrieve/Update/Destroy).
    """
    def has_object_permission(self, request, view, obj):
        # Lecture autorisée
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        role = getattr(user, 'role', None)
        # admin toujours OK
        if role == 'admin':
            return True
        # coach du groupe
        return getattr(obj, 'coach_id', None) == getattr(user, 'id', None)

    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) in ('admin', 'coach')