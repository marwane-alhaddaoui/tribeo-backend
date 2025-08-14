# apps/sport_sessions/api/serializers/session_serializer.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.sport_sessions.models import SportSession, SessionExternalAttendee   # ⬅️ ajout SessionExternalAttendee
from apps.sports.api.serializers.sport_serializer import SportSerializer
from apps.groups.models import Group, GroupMember, GroupExternalMember          # ⬅️ ajout GroupExternalMember
import requests
from django.utils.functional import cached_property

User = get_user_model()

class UserMiniSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ("id", "username", "email", "avatar_url")
    def get_avatar_url(self, obj):
        return getattr(obj, "avatar_url", None)

class SessionSerializer(serializers.ModelSerializer):
    creator = UserMiniSerializer(read_only=True)
    participants = UserMiniSerializer(many=True, read_only=True)
    sport = SportSerializer(read_only=True)
    sport_id = serializers.IntegerField(write_only=True, required=False)
    visibility = serializers.ChoiceField(
        choices=SportSession.Visibility.choices,
        default=SportSession.Visibility.PRIVATE
    )
    group_id = serializers.PrimaryKeyRelatedField(
        source='group',
        queryset=Group.objects.all(),
        required=False,
        allow_null=True
    )
    available_slots = serializers.SerializerMethodField()
    team_count = serializers.SerializerMethodField()
    
      # NEW:
    is_full = serializers.SerializerMethodField()
    computed_status = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = SportSession
        fields = [
            'id','title','sport','sport_id','description','location',
            'latitude','longitude','date','start_time','event_type','format',
            'status','requires_approval','home_team','away_team','score_home',
            'score_away','visibility','group_id','is_public','team_mode',
            'max_players','min_players_per_team','max_players_per_team',
            'creator','participants','created_at','updated_at',
            'available_slots','team_count',
            # NEW:
            'is_full','computed_status','actions',
        ]
        read_only_fields = [
            'creator','participants','created_at','updated_at',
            'latitude','longitude','status','is_public',
             # NEW:
            'is_full','computed_status','actions','available_slots'
        ]

    def get_available_slots(self, obj):
        if obj.max_players is None:
            return 0
    # 🔁 prend en compte externes + internes
        return max(obj.max_players - obj.attendees_count(), 0)

    def get_team_count(self, obj):
        return 2 if obj.team_mode else 1

    def validate(self, attrs):
        fmt = attrs.get('format', getattr(self.instance, 'format', None))
        group = attrs.get('group', getattr(self.instance, 'group', None))
        sport_id = attrs.get('sport_id', getattr(self.instance, 'sport_id', None))

        if fmt == SportSession.Format.VERSUS_TEAM:
            if not attrs.get('home_team') or not attrs.get('away_team'):
                raise serializers.ValidationError("Pour un format Équipe vs Équipe, home_team et away_team sont obligatoires.")
        if fmt == SportSession.Format.VERSUS_1V1:
            if attrs.get('max_players') != 2:
                raise serializers.ValidationError("Pour un format 1v1, max_players doit être égal à 2.")

        if attrs.get('team_mode'):
            min_pt = attrs.get('min_players_per_team')
            max_pt = attrs.get('max_players_per_team')
            if not max_pt:
                raise serializers.ValidationError("Si team_mode est activé, max_players_per_team est requis.")
            if min_pt and min_pt > max_pt:
                raise serializers.ValidationError("min_players_per_team ne peut pas être supérieur à max_players_per_team.")

        if attrs.get('visibility') == SportSession.Visibility.GROUP and not group:
            raise serializers.ValidationError("Un group_id est obligatoire pour une session de type GROUP.")

        # Héritage du sport depuis le groupe
        if group:
            if sport_id and sport_id != group.sport_id:
                raise serializers.ValidationError("La session d’un groupe doit utiliser le même sport que le groupe.")
            attrs['sport_id'] = group.sport_id
        else:
            if not sport_id:
                raise serializers.ValidationError({"sport_id": "Obligatoire si la session n'est pas liée à un groupe."})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        sport_id = validated_data.pop('sport_id')
        creator = self.context['request'].user
        validated_data['creator'] = creator

        # Géocodage best-effort
        location_text = validated_data.get('location')
        if location_text:
            try:
                resp = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": location_text, "format": "json", "limit": 1},
                    headers={"User-Agent": "TribeoApp/1.0"}
                )
                data = resp.json()
                if data:
                    validated_data["latitude"] = float(data[0]["lat"])
                    validated_data["longitude"] = float(data[0]["lon"])
            except Exception:
                pass

        session = SportSession.objects.create(sport_id=sport_id, **validated_data)

        # ajoute le créateur
        session.participants.add(creator)

        if session.group_id:
            try:
                active_status = GroupMember.STATUS_ACTIVE
            except AttributeError:
                active_status = 'ACTIVE'

            # internes
            ids = list(
                GroupMember.objects
                .filter(group_id=session.group_id, status=active_status)
                .exclude(user_id=session.creator_id)
                .values_list("user_id", flat=True)
            )
            unique_ids = {int(i) for i in ids if i}
            if unique_ids:
                session.participants.add(*unique_ids)

            # externes
            externals = GroupExternalMember.objects.filter(group_id=session.group_id) \
                                                   .values("first_name", "last_name", "note")
            for ext in externals:
                fn = (ext.get("first_name") or "").strip()
                ln = (ext.get("last_name") or "").strip()
                note = ext.get("note") or ""
                if not (fn or ln):
                    continue
                SessionExternalAttendee.objects.get_or_create(
                    session=session,
                    first_name=fn,
                    last_name=ln,
                    defaults={"note": note}
                )

        return session
    
     # NEW
    def get_is_full(self, obj):
        try:
            return obj.is_full()
        except Exception:
            return False

    def get_computed_status(self, obj):
        """
        On expose 'FULL' (affichage) quand DB=LOCKED.
        """
        try:
            status = obj.compute_status() if hasattr(obj, "compute_status") else (obj.status or "OPEN")
            if status == obj.Status.LOCKED and obj.is_full() and not obj.has_started():
                return "FULL"
            return status
        except Exception:
            return obj.status or "OPEN"

    def get_actions(self, obj):
        req = self.context.get("request")
        user = getattr(req, "user", None)
        is_auth = bool(user and user.is_authenticated)
        is_creator = is_auth and user == obj.creator
        is_participant = is_auth and obj.participants.filter(pk=user.pk).exists()

        # statut courant à l’instant T (sans créer d’effet de bord)
        status = self.get_computed_status(obj)
        is_past = obj.has_started()
        is_final = status in ["CANCELED", "FINISHED"]

        can_join = is_auth and (not is_final) and (not is_past) and (not obj.is_full()) and (not is_participant)
        # 💡 créateur ne peut plus quitter sa propre session
        can_leave = is_auth and is_participant and (not is_final) and (not is_past) and (not is_creator)

        return {
            "can_join": can_join,
            "can_leave": can_leave,
        }
