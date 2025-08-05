from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer

class LeaveSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)

        # Vérifier si l'utilisateur est inscrit
        if request.user not in session.participants.all():
            return Response({"detail": "Vous n'êtes pas inscrit à cette session."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Retirer l'utilisateur de la session
        session.participants.remove(request.user)
        session.save()

        return Response(SessionSerializer(session).data, status=status.HTTP_200_OK)
