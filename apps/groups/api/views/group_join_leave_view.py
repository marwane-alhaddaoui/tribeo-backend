from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from apps.groups.models import Group, GroupMember, GroupJoinRequest
from apps.groups.api.serializers.group_serializer import GroupDetailSerializer

from rest_framework.exceptions import ValidationError
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


class JoinGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)

        # Le owner est "déjà dedans"
        if group.owner_id == request.user.id:
            ser = GroupDetailSerializer(group, context={"request": request})
            return Response(ser.data, status=status.HTTP_200_OK)

        # Coach-only (invitation uniquement via demandes)
        if group.group_type == Group.GroupType.COACH:
            return Response(
                {"detail": "Ce groupe est sur invitation uniquement."},
                status=status.HTTP_403_FORBIDDEN
            )

        # --- Aucun quota pour rejoindre ---

        if group.group_type == Group.GroupType.OPEN:
            # Activation immédiate
            gm, created = GroupMember.objects.get_or_create(
                group=group,
                user=request.user,
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
                _safe_inc_usage_joined(request.user)  # no-op si champ absent

            ser = GroupDetailSerializer(group, context={"request": request})
            return Response(ser.data, status=status.HTTP_200_OK)

        if group.group_type == Group.GroupType.PRIVATE:
            # Crée/repasse en attente une demande (pas d'incrément d'usage ici)
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

        # Pas de décrément d'usage (compteur monotone)
        gm.delete()
        return Response({"left": True}, status=status.HTTP_200_OK)
