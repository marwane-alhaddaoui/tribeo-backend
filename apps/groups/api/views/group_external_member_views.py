from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from apps.groups.models import Group, GroupExternalMember
from apps.groups.api.permissions.group_permissions import IsGroupOwner
from apps.groups.api.serializers.group_serializer import ExternalMemberSerializer

class ExternalMemberListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupOwner]
    serializer_class = ExternalMemberSerializer

    def get_queryset(self):
        group = get_object_or_404(Group, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, group)
        return group.external_members.order_by("-id")

    def perform_create(self, serializer):
        group = get_object_or_404(Group, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, group)
        if not self.request.data.get("first_name") or not self.request.data.get("last_name"):
            raise ValidationError({"detail": "first_name and last_name are required."})
        serializer.save(group=group)

class ExternalMemberDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupOwner]
    queryset = GroupExternalMember.objects.all()
    lookup_url_kwarg = "eid"

    def perform_destroy(self, instance):
        self.check_object_permissions(self.request, instance.group)
        return super().perform_destroy(instance)
