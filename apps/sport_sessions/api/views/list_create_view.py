from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer
from apps.groups.models import GroupMember
from rest_framework.exceptions import ValidationError
from apps.billing.services.quotas import usage_for, get_limits_for

class SessionListCreateView(generics.ListCreateAPIView):
    """
    GET:
        - Accessible publiquement (visiteurs non connectés).
        - Anonyme  → uniquement les sessions publiques (is_public=True).
        - Authentifié :
            - ?mine=true        → uniquement les sessions créées ou rejointes par l'utilisateur
            - ?is_public=true   → uniquement les sessions publiques
            - Sinon :
                - User standard → sessions publiques
                - Coach/Admin   → toutes les sessions
        - Filtres communs (anonyme et connecté) :
            - ?sport_id=
            - ?search=
            - ?date_from=YYYY-MM-DD & ?date_to=YYYY-MM-DD (inclusif)

    POST:
        - Auth requis.
        - User standard → sessions publiques uniquement (force is_public=True)
        - Coach/Admin   → publiques, privées ou groupe
    """
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]  # défaut: privé

    # ✅ Ouvre le GET (liste) à tout le monde, garde POST privé
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        p = self.request.query_params

        # ==== BASE OPTIMISÉE (step 5) ====
        qs = (SportSession.objects
              .select_related("creator", "sport", "group", "home_team", "away_team")
              .prefetch_related("participants", "external_attendees"))

        # ---- Filtres communs ----
        if p.get("sport_id"):
            qs = qs.filter(sport_id=p["sport_id"])
        if p.get("group_id"):
            qs = qs.filter(group_id=p["group_id"])
        if p.get("event_type"):
            qs = qs.filter(event_type=p["event_type"])
        if p.get("city"):
            qs = qs.filter(city__iexact=p["city"])
        if p.get("search"):
            s = p["search"]
            qs = qs.filter(
                Q(title__icontains=s) |
                Q(description__icontains=s) |
                Q(location__icontains=s)
            )
        if p.get("date_from"):
            qs = qs.filter(date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(date__lte=p["date_to"])

        # ---- Visibilité / portée ----
        if not user:
            # Anonyme → uniquement PUBLIC
            qs = qs.filter(visibility=SportSession.Visibility.PUBLIC)

        else:
            # ?mine=true → sessions créées ou rejointes
            if p.get("mine") == "true":
                qs = qs.filter(Q(creator=user) | Q(participants=user))

            else:
                role = getattr(user, "role", None)

                # Base: PUBLIC ou où je suis participant
                scope = Q(visibility=SportSession.Visibility.PUBLIC) | Q(participants=user)

                # Si on cible un groupe précis ET que je suis membre actif → inclure ses GROUP
                gid = p.get("group_id")
                if gid and GroupMember.objects.filter(
                    group_id=gid, user=user, status=GroupMember.STATUS_ACTIVE
                ).exists():
                    scope |= Q(group_id=gid, visibility=SportSession.Visibility.GROUP)

                # Option admin/coach: tout voir si ?all=true
                if p.get("all") == "true" and role in ["admin", "coach"]:
                    pass  # ne filtre pas plus
                else:
                    qs = qs.filter(scope)

        return qs.order_by("-date", "-start_time", "-id").distinct()

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Auth requise."}, status=status.HTTP_401_UNAUTHORIZED)
    
       # --- QUOTA: création de sessions ---
        limits = get_limits_for(request.user)
        if limits["sessions_create_per_month"] is not None:
            uusage = usage_for(request.user)
            if uusage.sessions_created >= limits["sessions_create_per_month"]:
                raise ValidationError("Quota mensuel de création de sessions atteint pour votre plan.")
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(creator=request.user)
        session.participants.add(request.user)  # sécurité
        
        # --- incrément usage après succès ---
        uusage = usage_for(request.user)
        uusage.sessions_created += 1
        uusage.save()
        
    
        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)
