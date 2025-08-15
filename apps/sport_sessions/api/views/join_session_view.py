# apps/sport_sessions/api/views/join_session_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer
from apps.groups.models import GroupMember

# Quotas / limites (⇒ on n'importe QUE depuis billing.services.quotas)
from apps.billing.services.quotas import (
    usage_for,           # si tu en as besoin ailleurs
    get_limits_for,      # exposé par le service (normalisé)
    can_participate,
    increment_usage,
)


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

        # 📏 Quotas: participation à des sessions (depuis settings.PLAN_LIMITS normalisé)
        if not can_participate(request.user):
            # (optionnel) tu peux logger limits/usage si besoin de debug
            # limits = get_limits_for(request.user)
            raise ValidationError("Quota mensuel de participation atteint.")

        # 🧮 Capacité
        if session.is_full():
            return Response(
                {"detail": "La session est complète."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ➕ Inscription
        session.participants.add(request.user)
        # met à jour le statut après join (peut passer à FULL)
        try:
            session.apply_status(persist=True)
        except Exception:
            pass

        # 🔢 Incrément usage (champ réel: participations)
        increment_usage(request.user, participations=1)

        # 🔁 Retour avec context pour computed_status/actions
        return Response(
            SessionSerializer(session, context={"request": request}).data,
            status=status.HTTP_200_OK
        )
