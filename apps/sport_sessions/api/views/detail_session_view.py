from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer

class SessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Afficher / modifier / supprimer une session.
    Seul le créateur ou un admin peut modifier/supprimer.
    """
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # évite N+1 : charge creator + sport + group + teams, et précharge participants
        return (SportSession.objects
                .select_related("sport", "creator", "group", "home_team", "away_team")
                .prefetch_related("participants"))

    def perform_update(self, serializer):
        session = self.get_object()
        user = self.request.user
        if user != session.creator and getattr(user, "role", None) != "admin":
            raise PermissionDenied("Vous n'avez pas l'autorisation de modifier cette session.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if user != instance.creator and getattr(user, "role", None) != "admin":
            raise PermissionDenied("Vous n'avez pas l'autorisation de supprimer cette session.")
        instance.delete()
