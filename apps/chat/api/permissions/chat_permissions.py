# apps/chat/api/permissions/chat_permissions.py
from rest_framework.permissions import BasePermission
from apps.groups.models import GroupMember
from apps.sport_sessions.models import SportSession

class IsGroupMember(BasePermission):
    """
    Autorise seulement les membres du groupe (lecture/écriture).
    """
    def has_permission(self, request, view):
        gid = view.kwargs.get('group_id')
        user = getattr(request, "user", None)
        if not gid or not user or not user.is_authenticated:
            return False
        return GroupMember.objects.filter(group_id=gid, user=user).exists()


class IsSessionParticipant(BasePermission):
    """
    Autorise seulement le créateur de la session OU un participant (M2M).
    """
    def has_permission(self, request, view):
        sid = view.kwargs.get('session_id')
        user = getattr(request, "user", None)
        if not sid or not user or not user.is_authenticated:
            return False

        # Créateur autorisé
        if SportSession.objects.filter(id=sid, creator=user).exists():
            return True

        # Participant autorisé (M2M)
        if SportSession.objects.filter(id=sid, participants=user).exists():
            return True

        return False

class IsSessionParticipant(BasePermission):
    def has_permission(self, request, view):
        sid = view.kwargs.get('session_id')
        user = getattr(request, "user", None)
        if not sid or not user or not user.is_authenticated:
            return False
        if SportSession.objects.filter(id=sid, creator=user).exists():
            return True
        if SportSession.objects.filter(id=sid, participants=user).exists():
            return True
        return False
