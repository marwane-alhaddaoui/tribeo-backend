# apps/sport_sessions/api/serializers/session_serializer.py
from rest_framework import serializers
from apps.sport_sessions.models import SportSession
from apps.sports.api.serializers.sport_serializer import SportSerializer

class SessionSerializer(serializers.ModelSerializer):
    creator = serializers.ReadOnlyField(source='creator.email')
    participants = serializers.SlugRelatedField(
        many=True,
        slug_field='email',
        read_only=True
    )

    sport = SportSerializer(read_only=True)  # lecture
    sport_id = serializers.IntegerField(write_only=True)  # écriture

    class Meta:
        model = SportSession
        fields = [
            'id',
            'title',
            'sport',        # lecture
            'sport_id',     # écriture
            'description',
            'location',
            'date',
            'start_time',
            'is_public',
            'team_mode',
            'max_players',
            'min_players_per_team',
            'max_players_per_team',
            'creator',
            'participants',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['creator', 'participants', 'created_at', 'updated_at']

    def create(self, validated_data):
        sport_id = validated_data.pop('sport_id')
        return SportSession.objects.create(sport_id=sport_id, **validated_data)
