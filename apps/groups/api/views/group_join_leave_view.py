from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.groups.models.group import Group
from apps.groups.api.serializers.group_serializer import GroupSerializer

class JoinGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        if group.members.filter(id=request.user.id).exists():
            return Response({"detail": "Vous êtes déjà membre de ce groupe."},
                            status=status.HTTP_400_BAD_REQUEST)
        group.members.add(request.user)
        group.save()
        return Response(GroupSerializer(group).data, status=status.HTTP_200_OK)


class LeaveGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        if not group.members.filter(id=request.user.id).exists():
            return Response({"detail": "Vous n'êtes pas membre de ce groupe."},
                            status=status.HTTP_400_BAD_REQUEST)
        group.members.remove(request.user)
        group.save()
        return Response(GroupSerializer(group).data, status=status.HTTP_200_OK)
