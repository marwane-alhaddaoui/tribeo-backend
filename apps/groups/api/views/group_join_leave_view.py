# apps/groups/api/views/group_join_leave_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from apps.groups.models import Group, GroupMember, GroupJoinRequest
from apps.groups.api.serializers.group_serializer import GroupDetailSerializer

class JoinGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)

        if group.owner_id == request.user.id:
            ser = GroupDetailSerializer(group, context={"request": request})
            return Response(ser.data, status=status.HTTP_200_OK)

        if group.group_type == Group.GroupType.COACH:
            return Response({"detail": "Ce groupe est sur invitation uniquement."},
                            status=status.HTTP_403_FORBIDDEN)

        if group.group_type == Group.GroupType.OPEN:
            gm, created = GroupMember.objects.get_or_create(
                group=group, user=request.user,
                defaults={"role": GroupMember.ROLE_MEMBER, "status": GroupMember.STATUS_ACTIVE}
            )
            if not created and gm.status != GroupMember.STATUS_ACTIVE:
                gm.status = GroupMember.STATUS_ACTIVE
                gm.save(update_fields=["status"])
            ser = GroupDetailSerializer(group, context={"request": request})
            return Response(ser.data, status=status.HTTP_200_OK)

        if group.group_type == Group.GroupType.PRIVATE:
            jr, created = GroupJoinRequest.objects.get_or_create(group=group, user=request.user)
            if jr.status == GroupJoinRequest.REJECTED:
                jr.status = GroupJoinRequest.PENDING
                jr.save(update_fields=["status"])
            return Response({"requested": True}, status=status.HTTP_202_ACCEPTED)

        return Response({"detail": "Type de groupe inconnu."}, status=status.HTTP_400_BAD_REQUEST)

class LeaveGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)

        if group.owner_id == request.user.id:
            return Response(
                {"detail": "Le propriétaire doit transférer la propriété avant de quitter le groupe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        gm = GroupMember.objects.filter(group=group, user=request.user).first()
        if not gm:
            return Response({"detail": "Vous n'êtes pas membre de ce groupe."},
                            status=status.HTTP_400_BAD_REQUEST)

        gm.delete()
        return Response({"left": True}, status=status.HTTP_200_OK)
