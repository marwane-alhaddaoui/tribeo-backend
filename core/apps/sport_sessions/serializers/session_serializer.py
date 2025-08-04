from rest_framework import serializers
from sport_sessions.models import SportSession

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
            'location',
            'date',
            'start_time',
            'max_participants',
            'description',
            'creator',
            'participants',
            'created_at',
            'updated_at',
        ]
