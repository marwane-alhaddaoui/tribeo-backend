from rest_framework import permissions

class IsCoachOrAdmin(permissions.BasePermission):
    """
    Autorise uniquement les coaches et admins à créer ou gérer des groupes.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['coach', 'admin']
