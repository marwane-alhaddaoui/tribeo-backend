from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer
from apps.groups.models import GroupMember

# Quotas / limites
from apps.billing.services.quotas import usage_for              # compteurs d'usage utilisateur
from apps.users.utils.plan_limits import get_limits_for         # limites normalisées depuis settings.PLAN_LIMITS


class JoinSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)

        # 🔒 Sessions de groupe : réservé aux membres actifs du groupe
        if session.visibility == SportSession.Visibility.GROUP and session.group_id:
            is_member = GroupMember.objects.filter(
                group=session.group,
                user=request.user,
                status=GroupMember.STATUS_ACTIVE
            ).exists()
            if not is_member:
                return Response(
                    {"detail": "Accès réservé aux membres du groupe."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # 🔄 Synchroniser l'état avant action
        session.apply_status(persist=True)
        if session.has_started() or session.status in [
            SportSession.Status.CANCELED,
            SportSession.Status.FINISHED,
            SportSession.Status.LOCKED,
        ]:
            return Response(
                {"detail": "La session n'est pas joignable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Déjà inscrit ?
        if session.participants.filter(pk=request.user.pk).exists():
            return Response(
                SessionSerializer(session, context={"request": request}).data,
                status=status.HTTP_200_OK
            )

        # 📏 Quotas: participation à des sessions
        limits = get_limits_for(request.user)      # dict complet normalisé
        max_join = limits["sessions_join_per_month"]   # int ou None (illimité)
        if isinstance(max_join, int):
            uusage = usage_for(request.user)
            if uusage.sessions_joined >= max_join:
                raise ValidationError("Quota mensuel de participation atteint pour votre plan.")

        # 🧮 Capacité
        if session.is_full():
            return Response(
                {"detail": "La session est complète."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ➕ Inscription
        session.participants.add(request.user)
        session.apply_status(persist=True)  # met à jour le statut après join

        # 🔢 Incrément usage
        uusage = usage_for(request.user)
        uusage.sessions_joined += 1
        uusage.save()

        # 🔁 Retour avec context pour computed_status/actions
        return Response(
            SessionSerializer(session, context={"request": request}).data,
            status=status.HTTP_200_OK
        )
