from rest_framework import serializers
from apps.sport_sessions.models import SportSession

class SessionSerializer(serializers.ModelSerializer):
    creator = serializers.ReadOnlyField(source='creator.email')
    participants = serializers.SlugRelatedField(
        many=True,
        slug_field='email',
        read_only=True
    )

    class Meta:
        model = SportSession
        fields = [
            'id',
            'title',
            'sport',
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
        read_only_fields = [
            'creator',
            'participants',
            'created_at',
            'updated_at'
        ]
