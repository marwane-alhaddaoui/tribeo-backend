from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer


class LeaveSessionView(APIView):
    """
    Permet à un utilisateur de quitter une session s'il est inscrit.
    ⚠️ Le créateur ne peut pas quitter sa propre session.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)

        # Créateur: interdit de quitter
        if request.user == session.creator:
            return Response(
                {"detail": "Le créateur ne peut pas quitter sa propre session. Supprime la session si besoin."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Pas inscrit ?
        if not session.participants.filter(pk=request.user.pk).exists():
            return Response(
                {"detail": "Vous n'êtes pas inscrit à cette session."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # État courant: terminé/annulé → pas d’action
        session.apply_status(persist=True)
        if session.has_started() or session.status in [SportSession.Status.CANCELED, SportSession.Status.FINISHED]:
            return Response(
                {"detail": "La session est terminée ou annulée."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retirer + resynchroniser statut
        session.participants.remove(request.user)
        session.apply_status(persist=True)

        return Response(
            SessionSerializer(session, context={"request": request}).data,
            status=status.HTTP_200_OK
        )
