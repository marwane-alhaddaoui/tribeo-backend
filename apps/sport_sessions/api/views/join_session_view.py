from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer

class JoinSessionView(APIView):
    """
    Permet à un utilisateur de rejoindre une session ouverte
    si elle n'est pas complète et qu'il n'est pas déjà inscrit.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)

        # Vérifier si session publique
        if not session.is_public and request.user != session.creator:
            return Response(
                {"detail": "Vous ne pouvez pas rejoindre cette session privée."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Déjà inscrit ?
        if session.participants.filter(id=request.user.id).exists():
            return Response(
                {"detail": "Vous êtes déjà inscrit à cette session."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Session complète ?
        if session.is_full():
            return Response(
                {"detail": "La session est déjà complète."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ajout du participant
        session.participants.add(request.user)
        session.save()

        return Response(SessionSerializer(session).data, status=status.HTTP_200_OK)
