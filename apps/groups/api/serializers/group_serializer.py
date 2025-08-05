from rest_framework import serializers
from apps.groups.models.group import Group

class GroupSerializer(serializers.ModelSerializer):
    coach = serializers.ReadOnlyField(source='coach.email')
    members = serializers.SlugRelatedField(
        many=True,
        slug_field='email',
        read_only=True
    )

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'coach',
            'members', 'created_at', 'updated_at'
        ]
        read_only_fields = ['coach', 'members', 'created_at', 'updated_at']
