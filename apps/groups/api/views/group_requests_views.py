from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.groups.models import Group, GroupJoinRequest, GroupMember
from apps.groups.api.permissions.group_permissions import IsGroupOwner
from apps.groups.api.serializers.group_serializer import JoinRequestSerializer

class ListJoinRequestsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupOwner]
    serializer_class = JoinRequestSerializer

    def get_queryset(self):
        group = get_object_or_404(Group, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, group)
        status_filter = self.request.query_params.get("status")
        qs = group.join_requests.select_related("user").order_by("-created_at")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

class ApproveJoinRequestView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupOwner]

    def post(self, request, pk, rid):
        group = get_object_or_404(Group, pk=pk)
        self.check_object_permissions(request, group)
        jr = get_object_or_404(GroupJoinRequest, id=rid, group=group, status=GroupJoinRequest.PENDING)
        GroupMember.objects.get_or_create(
            group=group, user=jr.user,
            defaults={"role": GroupMember.ROLE_MEMBER, "status": GroupMember.STATUS_ACTIVE}
        )
        jr.status = GroupJoinRequest.APPROVED
        jr.save(update_fields=["status"])
        return Response({"approved": True}, status=status.HTTP_200_OK)

class RejectJoinRequestView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupOwner]

    def post(self, request, pk, rid):
        group = get_object_or_404(Group, pk=pk)
        self.check_object_permissions(request, group)
        jr = get_object_or_404(GroupJoinRequest, id=rid, group=group, status=GroupJoinRequest.PENDING)
        jr.status = GroupJoinRequest.REJECTED
        jr.save(update_fields=["status"])
        return Response({"rejected": True}, status=status.HTTP_200_OK)
