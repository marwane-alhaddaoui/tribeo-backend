# apps/chat/api/views/group_chat_views.py
from rest_framework import generics, status
from rest_framework.response import Response
from django.utils.timezone import now

from apps.chat.models import ChatMessage
from apps.chat.api.serializers.chat_message_serializer import ChatMessageSerializer
from apps.chat.api.permissions.chat_permissions import IsGroupMember
from apps.groups.models import Group, GroupMember  # ⬅️ ajouter GroupMember

def _is_group_owner(user, group: Group) -> bool:
    return getattr(group, 'owner_id', None) == user.id

def _is_group_manager(user, group: Group) -> bool:
    # manager OU owner via GroupMember
    return GroupMember.objects.filter(
        group=group, user=user,
        role__in=[GroupMember.ROLE_MANAGER, GroupMember.ROLE_OWNER],
        status=GroupMember.STATUS_ACTIVE
    ).exists()

def can_delete_group_msg(user, msg: ChatMessage):
    # Admins
    if user.is_staff or user.is_superuser:
        return True
    # Auteur
    if msg.sender_id == user.id:
        return True
    # Owner/Manager via GroupMember (ou owner FK direct)
    group = msg.group or Group.objects.filter(id=msg.group_id).first()
    if not group:
        return False
    if _is_group_owner(user, group):
        return True
    if _is_group_manager(user, group):
        return True
    return False


class GroupChatListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsGroupMember]

    def get_queryset(self):
        gid = self.kwargs['group_id']
        return ChatMessage.objects.filter(group_id=gid)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['can_delete_cb'] = lambda user, obj: can_delete_group_msg(user, obj)
        return ctx

    def perform_create(self, serializer):
        gid = self.kwargs['group_id']
        serializer.save(sender=self.request.user, group_id=gid)


class GroupChatDeleteView(generics.DestroyAPIView):
    permission_classes = [IsGroupMember]
    queryset = ChatMessage.objects.all()
    lookup_url_kwarg = 'msg_id'

    def delete(self, request, *args, **kwargs):
        msg: ChatMessage = self.get_object()
        if not can_delete_group_msg(request.user, msg):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        msg.is_deleted = True
        msg.deleted_at = now()
        msg.deleted_by = request.user
        msg.content = ''
        msg.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'content'])
        return Response(status=status.HTTP_204_NO_CONTENT)
