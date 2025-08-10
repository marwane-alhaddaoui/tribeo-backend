from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer


class SessionListCreateView(generics.ListCreateAPIView):
    """
    GET:
        - ?mine=true        → uniquement les sessions créées ou rejointes par l'utilisateur
        - ?is_public=true   → uniquement les sessions publiques (peu importe le rôle)
        - ?date_from=YYYY-MM-DD & ?date_to=YYYY-MM-DD → filtre par plage de dates (inclusif)
        - Sinon :
            - User standard → sessions publiques
            - Coach/Admin   → toutes les sessions

    POST:
        - User standard → sessions publiques uniquement
        - Coach/Admin   → publiques, privées ou groupe
    """
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        mine = params.get('mine') == 'true'
        public_only = params.get('is_public') == 'true'
        sport_id = params.get('sport_id')
        search = params.get('search')
        date_from = params.get('date_from')
        date_to = params.get('date_to')

        # 🔹 Dashboard perso
        if mine:
            queryset = SportSession.objects.filter(
                Q(creator=user) | Q(participants=user)
            ).distinct()
        else:
            # 🔹 Forcer l'affichage public pour tout le monde si demandé
            if public_only:
                queryset = SportSession.objects.filter(is_public=True)
            else:
                # 🔹 Logique par rôle
                role = getattr(user, 'role', None)
                if role in ['admin', 'coach']:
                    queryset = SportSession.objects.all()
                else:
                    queryset = SportSession.objects.filter(is_public=True)

        # 🎯 Filtres additionnels
        if sport_id:
            queryset = queryset.filter(sport_id=sport_id)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )

        # 📅 Plage de dates (inclusif)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        # Tri par date/heure (proche → loin)
        return queryset.order_by('date', 'start_time')

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data.copy()

        # Forcer public si pas admin/coach
        role = getattr(user, 'role', None)
        if role not in ['admin', 'coach']:
            data['is_public'] = True
            data['visibility'] = SportSession.Visibility.PUBLIC  # sync visibility

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(creator=user)

        # ✅ Ajouter créateur comme participant
        session.participants.add(user)

        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)
