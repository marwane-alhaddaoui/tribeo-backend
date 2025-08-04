from rest_framework import generics, permissions
from sport_sessions.models import SportSession
from sport_sessions.serializers.session_serializer import SessionSerializer

class SessionListCreateView(generics.ListCreateAPIView):
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
