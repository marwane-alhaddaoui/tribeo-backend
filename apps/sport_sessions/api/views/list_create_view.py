from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Q

from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer
from apps.groups.models import GroupMember

# Quotas / limites — garder uniquement ces imports
from apps.billing.services.quotas import (
    can_create_session,
    can_create_training,
    increment_usage,
)
from apps.audit.utils import audit_log

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
        - User/Premium → création forcée en PUBLIC + event_type=FRIENDLY (jamais TRAINING).
        - Coach/Admin  → peut créer TRAINING (group obligatoire, visibility=GROUP) ou autre type.
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

        # country / city → alias sur location__icontains
        country = (p.get("country") or "").strip()
        if country:
            qs = qs.filter(location__icontains=country)

        city = (p.get("city") or "").strip()
        if city:
            qs = qs.filter(location__icontains=city)

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

        data = request.data.copy()

        # ---- Rôle & type ----
        role = (getattr(request.user, "role", "") or "").lower()
        is_coach_or_admin = role in ("coach", "admin")

        # Normalisation event_type; compat vieux clients: is_training=1/true -> TRAINING
        evt = str(data.get("event_type", "")).strip().upper()
        if not evt and _truthy(data.get("is_training", "false")):
            evt = "TRAINING"
            data["event_type"] = "TRAINING"  # on explicite

        # ---- Quotas + règles métier
        if not is_coach_or_admin:
            # User/Premium → jamais TRAINING
            if evt == "TRAINING":
                raise ValidationError("Seuls les coachs peuvent créer une session d'entraînement.")
            data["event_type"] = evt or "FRIENDLY"
            data["visibility"] = SportSession.Visibility.PUBLIC
            data.pop("group", None)
            data.pop("group_id", None)

            if not can_create_session(request.user):
                raise ValidationError("Quota de créations de sessions atteint pour votre plan.")
        else:
            # Coach/Admin
            if not evt:
                # défaut coach: TRAINING si rien envoyé (optionnel, mais pratique)
                evt = "TRAINING"
                data["event_type"] = "TRAINING"

            if evt == "TRAINING":
                gid = data.get("group") or data.get("group_id")
                if not gid:
                    raise ValidationError("Pour un entraînement, un group_id est obligatoire.")
                data["group"] = gid
                data["visibility"] = SportSession.Visibility.GROUP

                if not can_create_training(request.user):
                    raise ValidationError("Quota d'entraînements atteint pour votre plan.")
            else:
                if not can_create_session(request.user):
                    raise ValidationError("Quota de créations de sessions atteint pour votre plan.")

        # ---- Validation / création
        serializer = self.get_serializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # 🚫 Ne PAS passer is_training au save (le modèle ne connaît pas ce champ)
        session = serializer.save(creator=request.user)

        # Auto-participation du créateur si pas déjà présent
        if not session.participants.filter(pk=request.user.pk).exists():
            session.participants.add(request.user)

        # Statut initial puis synchro métier
        session.status = SportSession.Status.OPEN
        session.apply_status(persist=True)

        # ---- Compteurs d'usage
        if session.event_type == SportSession.EventType.TRAINING:
            increment_usage(request.user, trainings=1)
        else:
            increment_usage(request.user, sessions=1)
            
        try:
            audit_log(
            request,                   
            "session.create",          
            obj=session,               
            meta={
            "event_type": session.event_type,
            "visibility": session.visibility,
            "group_id": session.group_id,
            },
            )  # on log l'audit ici
        except Exception:
            pass

        return Response(
            self.get_serializer(session, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )
