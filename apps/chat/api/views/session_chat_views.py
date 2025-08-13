# apps/chat/api/views/session_chat_views.py
from rest_framework import generics, status
from rest_framework.response import Response
from django.utils.timezone import now

from apps.chat.models import ChatMessage
from apps.chat.api.serializers.chat_message_serializer import ChatMessageSerializer
from apps.chat.api.permissions.chat_permissions import IsSessionParticipant
from apps.sport_sessions.models import SportSession
from apps.groups.models import GroupMember  # ⬅️ ajouter

def can_delete_session_msg(user, msg: ChatMessage):
    # Admins
    if user.is_staff or user.is_superuser:
        return True
    # Auteur
    if msg.sender_id == user.id:
        return True

    session = msg.session or SportSession.objects.filter(id=msg.session_id).first()
    if not session:
        return False

    # Créateur de la session
    if getattr(session, 'creator_id', None) == user.id:
        return True

    # Owner/Manager du groupe parent (via GroupMember)
    group = getattr(session, 'group', None)
    if group:
        if getattr(group, 'owner_id', None) == user.id:
            return True
        if GroupMember.objects.filter(
            group=group, user=user,
            role__in=[GroupMember.ROLE_MANAGER, GroupMember.ROLE_OWNER],
            status=GroupMember.STATUS_ACTIVE
        ).exists():
            return True

    return False


class SessionChatListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsSessionParticipant]

    def get_queryset(self):
        sid = self.kwargs['session_id']
        return ChatMessage.objects.filter(session_id=sid)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['can_delete_cb'] = lambda user, obj: can_delete_session_msg(user, obj)
        return ctx

    def perform_create(self, serializer):
        sid = self.kwargs['session_id']
        serializer.save(sender=self.request.user, session_id=sid)


class SessionChatDeleteView(generics.DestroyAPIView):
    permission_classes = [IsSessionParticipant]
    queryset = ChatMessage.objects.all()
    lookup_url_kwarg = 'msg_id'

    def delete(self, request, *args, **kwargs):
        msg: ChatMessage = self.get_object()
        if not can_delete_session_msg(request.user, msg):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        msg.is_deleted = True
        msg.deleted_at = now()
        msg.deleted_by = request.user
        msg.content = ''
        msg.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'content'])
        return Response(status=status.HTTP_204_NO_CONTENT)
