from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer

class LeaveSessionView(APIView):
    """
    Permet à un utilisateur de quitter une session
    s'il est déjà inscrit. Les créateurs peuvent retirer
    eux-mêmes leur inscription s'ils ne souhaitent plus participer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)

        # Vérifier l'inscription
        if not session.participants.filter(id=request.user.id).exists():
            return Response(
                {"detail": "Vous n'êtes pas inscrit à cette session."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Si l'utilisateur est le créateur et seul participant
        if request.user == session.creator and session.participants.count() <= 1:
            return Response(
                {"detail": "Vous êtes le créateur et le seul participant. Supprimez la session si vous souhaitez l'annuler."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retirer l'utilisateur
        session.participants.remove(request.user)
        session.save()

        return Response(SessionSerializer(session).data, status=status.HTTP_200_OK)
