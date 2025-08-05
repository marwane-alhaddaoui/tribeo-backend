from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from apps.teams.models.team import Team
from apps.teams.api.serializers.team_serializer import TeamSerializer
from apps.sport_sessions.models.sport_session import SportSession

class TeamListCreateView(generics.ListCreateAPIView):
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Team.objects.filter(session_id=self.kwargs['session_id'])

    def perform_create(self, serializer):
        session = SportSession.objects.get(id=self.kwargs['session_id'])
        if self.request.user != session.creator and self.request.user.role != 'admin':
            raise PermissionDenied("Vous n'avez pas l'autorisation de créer une équipe.")
        serializer.save(session=session)


class TeamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        team = self.get_object()
        if self.request.user != team.session.creator and self.request.user.role != 'admin':
            raise PermissionDenied("Vous n'avez pas l'autorisation de modifier cette équipe.")
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user != instance.session.creator and self.request.user.role != 'admin':
            raise PermissionDenied("Vous n'avez pas l'autorisation de supprimer cette équipe.")
        instance.delete()
