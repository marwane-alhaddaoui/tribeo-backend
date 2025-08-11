# apps/users/api/serializers/user_serializer.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
import re

User = get_user_model()
USERNAME_RX = re.compile(r"^[a-z0-9_]{3,20}$")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    # On expose "role" côté lecture si besoin, mais on force 'user' dans create()
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='user', required=False)
    username = serializers.CharField(required=True)  # 🔒 obligatoire

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'role', 'username']

    def validate_username(self, v):
        v = (v or "").strip().lower()
        if not USERNAME_RX.match(v):
            raise serializers.ValidationError("3–20 caractères, a-z 0-9 _ uniquement.")
        if User.objects.filter(username__iexact=v).exists():
            raise serializers.ValidationError("Nom d'utilisateur déjà pris.")
        return v

    def create(self, validated_data):
        password = validated_data.pop('password')
        # On force la sécurité: personne ne choisit son rôle à l'inscription
        validated_data['role'] = 'user'
        username = validated_data.pop('username').strip().lower()

        user = User(username=username, **validated_data)
        user.set_password(password)
        user.full_clean()
        user.save()
        return user


# Pour lecture/écriture générique (admin / profil)
class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'role', 'is_active', 'date_joined']
        read_only_fields = ['email', 'date_joined', 'is_active', 'role']  # ajuste selon ton besoin

    def validate_username(self, v):
        v = (v or "").strip().lower()
        if not USERNAME_RX.match(v):
            raise serializers.ValidationError("3–20 caractères, a-z 0-9 _ uniquement.")
        qs = User.objects.filter(username__iexact=v)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Nom d'utilisateur déjà pris.")
        return v
