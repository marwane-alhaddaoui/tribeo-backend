from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.groups.models import Group, GroupMember
from apps.groups.api.serializers.group_serializer import GroupDetailSerializer

class JoinGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)

        # déjà owner ?
        if group.owner_id == request.user.id:
            ser = GroupDetailSerializer(group, context={"request": request})
            return Response(ser.data, status=status.HTTP_200_OK)

        gm, created = GroupMember.objects.get_or_create(
            group=group, user=request.user,
            defaults={"role": GroupMember.ROLE_MEMBER, "status": GroupMember.STATUS_ACTIVE}
        )
        if not created and gm.status != GroupMember.STATUS_ACTIVE:
            gm.status = GroupMember.STATUS_ACTIVE
            gm.save(update_fields=["status"])

        ser = GroupDetailSerializer(group, context={"request": request})
        return Response(ser.data, status=status.HTTP_200_OK)


class LeaveGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        # owner ne peut pas se retirer
        if group.owner_id == request.user.id:
            return Response({"detail": "Le propriétaire ne peut pas quitter son propre groupe."},
                            status=status.HTTP_400_BAD_REQUEST)

        gm = GroupMember.objects.filter(group=group, user=request.user).first()
        if not gm:
            return Response({"detail": "Vous n'êtes pas membre de ce groupe."},
                            status=status.HTTP_400_BAD_REQUEST)

        gm.delete()
        ser = GroupDetailSerializer(group, context={"request": request})
        return Response(ser.data, status=status.HTTP_200_OK)
