from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.groups.models.group import Group
from apps.users.models.users import CustomUser
from apps.groups.api.permissions.group_permissions import IsCoachOrAdmin

class AddMemberView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCoachOrAdmin]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        user = get_object_or_404(CustomUser, pk=request.data.get("user_id"))
        if group.members.filter(id=user.id).exists():
            return Response({"detail": "Cet utilisateur est déjà membre."},
                            status=status.HTTP_400_BAD_REQUEST)
        group.members.add(user)
        return Response({"detail": "Membre ajouté"}, status=status.HTTP_200_OK)


class RemoveMemberView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCoachOrAdmin]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        user = get_object_or_404(CustomUser, pk=request.data.get("user_id"))
        if not group.members.filter(id=user.id).exists():
            return Response({"detail": "Cet utilisateur n'est pas membre."},
                            status=status.HTTP_400_BAD_REQUEST)
        group.members.remove(user)
        return Response({"detail": "Membre retiré"}, status=status.HTTP_200_OK)
