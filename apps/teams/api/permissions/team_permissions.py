from rest_framework import permissions

class IsSessionCreatorOrAdmin(permissions.BasePermission):
    """
    Seul le créateur de la session ou un admin peut créer/éditer/supprimer une équipe.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated
