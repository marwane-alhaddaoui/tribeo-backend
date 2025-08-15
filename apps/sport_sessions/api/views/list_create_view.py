from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Q

from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer
from apps.groups.models import GroupMember

# Quotas / limites
from apps.billing.services.quotas import usage_for            # compteurs (usage utilisateur)
from apps.users.utils.plan_limits import get_limits_for       # limites normalisées (FREE/PREMIUM/COACH)


def _truthy(v) -> bool:
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}


class SessionListCreateView(generics.ListCreateAPIView):
    """
    GET:
        - Public (AllowAny).
        - Anonyme  → uniquement sessions publiques (visibility=PUBLIC).
        - Authentifié :
            - ?mine=true        → sessions créées ou rejointes par l'utilisateur
            - ?is_public=true   → uniquement publiques
            - Sinon :
                - User standard → publiques + celles où il est participant
                - Coach/Admin   → tout si ?all=true, sinon publiques + où il est participant
        Filtres communs:
            - ?sport_id=, ?group_id=, ?event_type=, ?search=
            - ?country=, ?city= (alias sur `location__icontains`)
            - ?date_from=YYYY-MM-DD, ?date_to=YYYY-MM-DD

    POST:
        - Auth requis.
        - User standard → création forcée en PUBLIC.
        - Coach/Admin   → PUBLIC / PRIVATE / GROUP autorisés.
    """
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]  # par défaut

    def get_permissions(self):
        # Ouvre le GET à tout le monde, POST reste protégé
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        p = self.request.query_params

        qs = (
            SportSession.objects
            .select_related("creator", "sport", "group", "home_team", "away_team")
            .prefetch_related("participants", "external_attendees")
        )

        # ---- Filtres communs ----
        if p.get("sport_id"):
            qs = qs.filter(sport_id=p["sport_id"])
        if p.get("group_id"):
            qs = qs.filter(group_id=p["group_id"])
        if p.get("event_type"):
            qs = qs.filter(event_type=p["event_type"])

        # ✅ BEST PRACTICE (modèle sans champs city/country) :
        # on mappe les paramètres country/city vers location__icontains
        country = (p.get("country") or "").strip()
        if country:
            qs = qs.filter(location__icontains=country)

        city = (p.get("city") or "").strip()
        if city:
            qs = qs.filter(location__icontains=city)  # gère aussi les CP (ex: "35460")

        if p.get("search"):
            s = p["search"].strip()
            if s:
                qs = qs.filter(
                    Q(title__icontains=s) |
                    Q(description__icontains=s) |
                    Q(location__icontains=s)
                )
        if p.get("date_from"):
            qs = qs.filter(date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(date__lte=p["date_to"])

        # Filtre explicite is_public si demandé
        if "is_public" in p and _truthy(p.get("is_public")):
            qs = qs.filter(visibility=SportSession.Visibility.PUBLIC)

        # ---- Visibilité / portée ----
        if not user:
            # Anonyme → uniquement PUBLIC
            qs = qs.filter(visibility=SportSession.Visibility.PUBLIC)
        else:
            # ?mine=true → sessions créées OU rejointes
            if _truthy(p.get("mine", "false")):
                qs = qs.filter(Q(creator=user) | Q(participants=user))
            else:
                role = (getattr(user, "role", "") or "").lower()

                # base: publiques + celles où je suis participant
                scope = Q(visibility=SportSession.Visibility.PUBLIC) | Q(participants=user)

                # Si on cible un groupe précis ET que je suis membre actif → inclure ses GROUP
                gid = p.get("group_id")
                if gid and GroupMember.objects.filter(
                    group_id=gid, user=user, status=GroupMember.STATUS_ACTIVE
                ).exists():
                    scope |= Q(group_id=gid, visibility=SportSession.Visibility.GROUP)

                # admin/coach peuvent tout voir si ?all=true
                if _truthy(p.get("all", "false")) and role in ("admin", "coach"):
                    pass  # pas de filtre supplémentaire
                else:
                    qs = qs.filter(scope)

        return qs.order_by("-date", "-start_time", "-id").distinct()

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Auth requise."}, status=status.HTTP_401_UNAUTHORIZED)

        # --- QUOTA: création de sessions ---
        limits = get_limits_for(request.user)  # dict normalisé depuis settings.PLAN_LIMITS
        uusage = usage_for(request.user)

        max_create = limits["sessions_create_per_month"]  # peut être int ou None (illimité)
        if isinstance(max_create, int) and uusage.sessions_created >= max_create:
            raise ValidationError("Quota mensuel de création de sessions atteint pour votre plan.")

        # Enforcement visibilité selon rôle
        data = request.data.copy()
        role = (getattr(request.user, "role", "") or "").lower()
        if role not in ("admin", "coach"):
            # User standard → force PUBLIC et annule une éventuelle cible group/private
            data["visibility"] = SportSession.Visibility.PUBLIC
            data.pop("group_id", None)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        # Save + auto-participation créateur
        session = serializer.save(creator=request.user)
        if not session.participants.filter(pk=request.user.pk).exists():
            session.participants.add(request.user)

        # Statut initial puis synchro
        session.status = SportSession.Status.OPEN
        session.apply_status(persist=True)

        # --- incrément usage après succès ---
        uusage.sessions_created += 1
        uusage.save()

        # Retour avec context pour actions/computed_status
        return Response(self.get_serializer(session, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)
