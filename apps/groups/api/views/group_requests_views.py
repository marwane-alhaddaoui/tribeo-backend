from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.groups.models import Group, GroupJoinRequest, GroupMember
from apps.groups.api.permissions.group_permissions import IsGroupOwner
from apps.groups.api.serializers.group_serializer import JoinRequestSerializer
from apps.billing.services.quotas import usage_for, get_limits_for


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

    @transaction.atomic
    def post(self, request, pk, rid):
        group = get_object_or_404(Group, pk=pk)
        self.check_object_permissions(request, group)

        jr = get_object_or_404(
            GroupJoinRequest,
            id=rid,
            group=group,
            status=GroupJoinRequest.PENDING
        )

        # --- QUOTA: nombre de groupes rejoints (comptage des memberships ACTIFS) ---
        limits = get_limits_for(jr.user)
        if limits["max_groups_joined"] is not None:
            already = GroupMember.objects.filter(
                user=jr.user,
                status=GroupMember.STATUS_ACTIVE
            ).count()
            if already >= limits["max_groups_joined"]:
                raise ValidationError("Nombre maximal de groupes atteint pour le plan de l’utilisateur.")

        # Création / activation du membership
        gm, created = GroupMember.objects.get_or_create(
            group=group,
            user=jr.user,
            defaults={"role": GroupMember.ROLE_MEMBER, "status": GroupMember.STATUS_ACTIVE}
        )

        activated_now = False
        if not created and gm.status != GroupMember.STATUS_ACTIVE:
            gm.status = GroupMember.STATUS_ACTIVE
            gm.save(update_fields=["status"])
            activated_now = True

        # Incrémente l'usage UNIQUEMENT si on vient d'activer un membership actif
        if (created and gm.status == GroupMember.STATUS_ACTIVE) or activated_now:
            uusage = usage_for(jr.user)
            uusage.groups_joined += 1
            uusage.save()

        # Marque la demande comme approuvée
        jr.status = GroupJoinRequest.APPROVED
        jr.save(update_fields=["status"])

        return Response({"approved": True}, status=status.HTTP_200_OK)


class RejectJoinRequestView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupOwner]

    def post(self, request, pk, rid):
        group = get_object_or_404(Group, pk=pk)
        self.check_object_permissions(request, group)
        jr = get_object_or_404(
            GroupJoinRequest,
            id=rid,
            group=group,
            status=GroupJoinRequest.PENDING
        )
        jr.status = GroupJoinRequest.REJECTED
        jr.save(update_fields=["status"])
        return Response({"rejected": True}, status=status.HTTP_200_OK)
