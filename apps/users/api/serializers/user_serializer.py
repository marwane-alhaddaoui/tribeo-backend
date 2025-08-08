# apps/users/api/serializers/user_serializer.py
from rest_framework import serializers
from apps.users.models import CustomUser

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=CustomUser.ROLE_CHOICES, default='user')

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'password', 'role']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


# ✅ Nouveau serializer pour l’admin
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined']
