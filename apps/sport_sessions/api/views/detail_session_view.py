from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer

class SessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        return obj

    def perform_update(self, serializer):
        session = self.get_object()
        # Vérifier que l'utilisateur est le créateur
        if self.request.user != session.creator:
            raise PermissionDenied("Vous n'avez pas l'autorisation de modifier cette session.")
        serializer.save()

    def perform_destroy(self, instance):
        # Vérifier que l'utilisateur est le créateur
        if self.request.user != instance.creator:
            raise PermissionDenied("Vous n'avez pas l'autorisation de supprimer cette session.")
        instance.delete()
