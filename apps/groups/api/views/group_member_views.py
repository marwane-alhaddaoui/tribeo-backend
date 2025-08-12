from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.groups.models import Group, GroupMember
from apps.users.models.users import CustomUser
from apps.groups.api.permissions.group_permissions import IsGroupOwnerOrManager
from apps.groups.api.serializers.group_serializer import GroupDetailSerializer

class AddMemberView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupOwnerOrManager]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        self.check_object_permissions(request, group)

        user = get_object_or_404(CustomUser, pk=request.data.get("user_id"))
        if user.id == group.owner_id:
            return Response({"detail": "L'owner est déjà membre."}, status=status.HTTP_400_BAD_REQUEST)

        gm, created = GroupMember.objects.get_or_create(
            group=group, user=user,
            defaults={"role": GroupMember.ROLE_MEMBER, "status": GroupMember.STATUS_ACTIVE}
        )
        if not created and gm.status != GroupMember.STATUS_ACTIVE:
            gm.status = GroupMember.STATUS_ACTIVE
            gm.save(update_fields=["status"])

        return Response(GroupDetailSerializer(group, context={"request": request}).data, status=status.HTTP_200_OK)


class RemoveMemberView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupOwnerOrManager]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        self.check_object_permissions(request, group)

        user = get_object_or_404(CustomUser, pk=request.data.get("user_id"))
        if user.id == group.owner_id:
            return Response({"detail": "Impossible de retirer l'owner."}, status=status.HTTP_400_BAD_REQUEST)

        gm = GroupMember.objects.filter(group=group, user=user).first()
        if not gm:
            return Response({"detail": "Cet utilisateur n'est pas membre."}, status=status.HTTP_400_BAD_REQUEST)

        gm.delete()
        return Response(GroupDetailSerializer(group, context={"request": request}).data, status=status.HTTP_200_OK)
