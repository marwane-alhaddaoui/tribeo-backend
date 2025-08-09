from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer
from apps.users.api.permissions.roles_permissions import IsAdminOrCoach

class SessionListCreateView(generics.ListCreateAPIView):
    """
    GET: Liste toutes les sessions disponibles (connecté uniquement).
    POST: Crée une session.
        - User standard: peut créer uniquement des sessions publiques.
        - Coach/Admin: peuvent créer publiques ou privées.
    """
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filtrer les sessions:
        - Les utilisateurs simples voient uniquement les sessions publiques.
        - Les admins/coachs voient tout.
        - Filtre supplémentaire : sport_id et search.
        """
        user = self.request.user
        queryset = SportSession.objects.all() if user.role in ['admin', 'coach'] else SportSession.objects.filter(is_public=True)

        # Filtre par sport_id
        sport_id = self.request.query_params.get('sport_id')
        if sport_id:
            queryset = queryset.filter(sport_id=sport_id)

        # Filtre par recherche
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data.copy()

        # Si l'utilisateur n'est pas admin/coach, on force la session à être publique
        if user.role not in ['admin', 'coach']:
            data['is_public'] = True

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(creator=user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
