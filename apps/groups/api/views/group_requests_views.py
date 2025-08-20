from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.groups.models import Group, GroupJoinRequest, GroupMember
from apps.groups.api.permissions.group_permissions import IsGroupOwner  # ou IsGroupModerator si tu l'utilises
from apps.groups.api.serializers.group_serializer import JoinRequestSerializer
from apps.billing.services.quotas import usage_for  # (facultatif: pour un compteur "safe")


def _safe_inc_usage_joined(user):
    """
    Incrémente un compteur 'join' uniquement si le champ existe sur l'objet usage.
    Sinon, no-op.
    """
    try:
        u = usage_for(user)
    except Exception:
        return
    for field in ("groups_joined", "memberships_joined", "groups"):
        if hasattr(u, field):
            cur = getattr(u, field) or 0
            try:
                cur = int(cur)
            except (TypeError, ValueError):
                cur = 0
            setattr(u, field, cur + 1)
            try:
                u.save(update_fields=[field])
            except Exception:
                u.save()
            return
    # aucun champ connu -> no-op


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

        # Pas de filtre sur le status -> idempotent
        jr = get_object_or_404(GroupJoinRequest, id=rid, group=group)
        target = jr.user

        # déjà approuvée → on supprime et OK
        if jr.status == GroupJoinRequest.APPROVED:
            jr.delete()
            return Response({"approved": True, "idempotent": True, "deleted": True}, status=status.HTTP_200_OK)

        # déjà membre actif → on supprime et OK
        gm_existing = GroupMember.objects.filter(
            group=group, user=target, status=GroupMember.STATUS_ACTIVE
        ).first()
        if gm_existing:
            jr.delete()
            return Response({"approved": True, "already_member": True, "deleted": True}, status=status.HTTP_200_OK)

        # --- Aucun quota pour rejoindre ---

        # Création / activation
        gm, created = GroupMember.objects.get_or_create(
            group=group,
            user=target,
            defaults={"role": GroupMember.ROLE_MEMBER, "status": GroupMember.STATUS_ACTIVE}
        )

        activated_now = False
        if not created and gm.status != GroupMember.STATUS_ACTIVE:
            gm.status = GroupMember.STATUS_ACTIVE
            gm.save(update_fields=["status"])
            activated_now = True
        elif created:
            activated_now = True

        if activated_now:
            _safe_inc_usage_joined(target)  # no-op si champ absent

        # on supprime la demande après succès
        jr.delete()
        return Response({"approved": True, "deleted": True}, status=status.HTTP_200_OK)


class RejectJoinRequestView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupOwner]

    @transaction.atomic
    def post(self, request, pk, rid):
        group = get_object_or_404(Group, pk=pk)
        self.check_object_permissions(request, group)

        jr = get_object_or_404(GroupJoinRequest, id=rid, group=group)

        # déjà rejetée → delete + 200 idempotent
        if jr.status == GroupJoinRequest.REJECTED:
            jr.delete()
            return Response({"rejected": True, "idempotent": True, "deleted": True}, status=status.HTTP_200_OK)

        jr.delete()
        return Response({"rejected": True, "deleted": True}, status=status.HTTP_200_OK)
