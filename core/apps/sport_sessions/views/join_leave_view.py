from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from sport_sessions.models import SportSession
from sport_sessions.serializers.session_serializer import SessionSerializer

class JoinSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)

        if request.user in session.participants.all():
            return Response({"detail": "Déjà inscrit à cette session."},
                            status=status.HTTP_400_BAD_REQUEST)

        if session.is_full():
            return Response({"detail": "Session complète."},
                            status=status.HTTP_400_BAD_REQUEST)

        session.participants.add(request.user)
        session.save()
        return Response(SessionSerializer(session).data, status=status.HTTP_200_OK)
