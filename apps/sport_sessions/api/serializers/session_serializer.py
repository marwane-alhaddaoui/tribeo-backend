# apps/sport_sessions/api/serializers/session_serializer.py
from rest_framework import serializers
from apps.sport_sessions.models import SportSession
from apps.sports.api.serializers.sport_serializer import SportSerializer
from apps.groups.models import Group  # <-- à vérifier selon ton arborescence
import requests


class SessionSerializer(serializers.ModelSerializer):
    creator = serializers.ReadOnlyField(source='creator.email')
    participants = serializers.SlugRelatedField(
        many=True,
        slug_field='email',
        read_only=True
    )

    sport = SportSerializer(read_only=True)  # lecture
    sport_id = serializers.IntegerField(write_only=True)  # écriture

    # 🔥 Nouveaux champs pour visibilité et groupe
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

    class Meta:
        model = SportSession
        fields = [
            'id',
            'title',
            'sport', 'sport_id',
            'description',
            'location',
            'latitude',
            'longitude',
            'date',
            'start_time',
            'event_type',
            'format',
            'status',
            'requires_approval',
            'home_team',
            'away_team',
            'score_home',
            'score_away',
            'visibility',  # 🆕
            'group_id',    # 🆕
            'is_public',
            'team_mode',
            'max_players',
            'min_players_per_team',
            'max_players_per_team',
            'creator',
            'participants',
            'created_at',
            'updated_at',
            'available_slots',
        ]
        read_only_fields = [
            'creator',
            'participants',
            'created_at',
            'updated_at',
            'latitude',
            'longitude',
            'status',
            'is_public',  # calculé dans save()
        ]

    def get_available_slots(self, obj):
        return max(obj.max_players - obj.participants.count(), 0)

    def validate(self, attrs):
        fmt = attrs.get('format', getattr(self.instance, 'format', None))

        # Format Équipe vs Équipe → home_team et away_team requis
        if fmt == SportSession.Format.VERSUS_TEAM:
            if not attrs.get('home_team') or not attrs.get('away_team'):
                raise serializers.ValidationError(
                    "Pour un format Équipe vs Équipe, home_team et away_team sont obligatoires."
                )

        # Format 1v1 → max_players doit être 2
        if fmt == SportSession.Format.VERSUS_1V1:
            if attrs.get('max_players') != 2:
                raise serializers.ValidationError(
                    "Pour un format 1v1, max_players doit être égal à 2."
                )

        # team_mode activé → max_players_per_team requis
        if attrs.get('team_mode'):
            if not attrs.get('max_players_per_team'):
                raise serializers.ValidationError(
                    "Si team_mode est activé, max_players_per_team est requis."
                )
            if attrs.get('min_players_per_team') and attrs['min_players_per_team'] > attrs['max_players_per_team']:
                raise serializers.ValidationError(
                    "min_players_per_team ne peut pas être supérieur à max_players_per_team."
                )

        # Visibilité GROUP → group obligatoire
        if attrs.get('visibility') == SportSession.Visibility.GROUP and not attrs.get('group'):
            raise serializers.ValidationError(
                "Un group_id est obligatoire pour une session de type GROUP."
            )

        return attrs

    def create(self, validated_data):
        sport_id = validated_data.pop('sport_id')
        creator = self.context['request'].user
        validated_data['creator'] = creator

        # 📍 Géocodage automatique
        location_text = validated_data.get('location')
        if location_text:
            try:
                response = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": location_text, "format": "json", "limit": 1},
                    headers={"User-Agent": "TribeoApp/1.0"}
                )
                data = response.json()
                if data:
                    validated_data["latitude"] = float(data[0]["lat"])
                    validated_data["longitude"] = float(data[0]["lon"])
            except Exception as e:
                print(f"Erreur géocodage : {e}")

        session = SportSession.objects.create(sport_id=sport_id, **validated_data)

        # Ajoute automatiquement le créateur comme participant
        session.participants.add(creator)

        return session
