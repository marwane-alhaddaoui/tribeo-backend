from rest_framework import serializers
from apps.teams.models.team import Team

class TeamSerializer(serializers.ModelSerializer):
    session = serializers.ReadOnlyField(source='session.id')
    members = serializers.SlugRelatedField(
        many=True,
        slug_field='email',
        read_only=True
    )

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'color', 'session',
            'members', 'created_at', 'updated_at'
        ]
        read_only_fields = ['session', 'members', 'created_at', 'updated_at']
