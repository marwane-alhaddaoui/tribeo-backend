from rest_framework import generics, permissions
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer
from apps.users.api.permissions.roles_permissions import IsAdminOrCoach

class SessionListCreateView(generics.ListCreateAPIView):
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer

    def get_permissions(self):
        # POST → réservé Admin & Coach
        if self.request.method == 'POST':
            return [IsAdminOrCoach()]
        # GET → tout utilisateur connecté
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
