from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer

class SessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Permet d'afficher, modifier ou supprimer une session sportive.
    Seul le créateur ou un administrateur peut modifier ou supprimer la session.
    """
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Récupère la session spécifique demandée.
        """
        return super().get_object()

    def perform_update(self, serializer):
        session = self.get_object()
        user = self.request.user

        # Vérifier que l'utilisateur a les droits
        if user != session.creator and user.role != 'admin':
            raise PermissionDenied("Vous n'avez pas l'autorisation de modifier cette session.")

        # Mise à jour
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        # Vérifier que l'utilisateur a les droits
        if user != instance.creator and user.role != 'admin':
            raise PermissionDenied("Vous n'avez pas l'autorisation de supprimer cette session.")

        instance.delete()
