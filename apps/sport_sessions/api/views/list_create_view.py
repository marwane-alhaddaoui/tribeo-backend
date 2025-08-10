from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer


class SessionListCreateView(generics.ListCreateAPIView):
    """
    GET:
        - ?mine=true → uniquement les sessions créées ou rejointes par l'utilisateur
        - ?is_public=true → uniquement les sessions publiques (peu importe le rôle)
        - Sinon :
            - User standard → sessions publiques
            - Coach/Admin → toutes les sessions

    POST:
        - User standard → sessions publiques uniquement
        - Coach/Admin → publiques, privées ou groupe
    """
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        mine = self.request.query_params.get('mine') == 'true'
        public_only = self.request.query_params.get('is_public') == 'true'

        # 🔹 Dashboard perso
        if mine:
            return SportSession.objects.filter(
                Q(creator=user) | Q(participants=user)
            ).distinct()

        # 🔹 Forcer l'affichage public pour tout le monde
        if public_only:
            queryset = SportSession.objects.filter(is_public=True)
        else:
            # 🔹 Logique par rôle
            if user.role in ['admin', 'coach']:
                queryset = SportSession.objects.all()
            else:
                queryset = SportSession.objects.filter(is_public=True)

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

        # Forcer public si pas admin/coach
        if user.role not in ['admin', 'coach']:
            data['is_public'] = True
            data['visibility'] = SportSession.Visibility.PUBLIC  # synchroniser avec enum

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(creator=user)

        # ✅ Ajouter créateur comme participant
        session.participants.add(user)

        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)
