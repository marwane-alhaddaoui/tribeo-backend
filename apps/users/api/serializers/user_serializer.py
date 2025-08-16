# apps/users/api/serializers/user_serializer.py
from django.conf import settings
from rest_framework import serializers
from django.contrib.auth import get_user_model
import re

User = get_user_model()
USERNAME_RX = re.compile(r"^[a-z0-9_]{3,20}$")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='user', required=False)
    username = serializers.CharField(required=True)

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
        # rôle forcé à user à l’inscription
        validated_data['role'] = 'user'
        username = validated_data.pop('username').strip().lower()

        user = User(username=username, **validated_data)
        user.set_password(password)
        user.full_clean()
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)
    avatar = serializers.ImageField(required=False, allow_null=True)
    avatar_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    avatar_src = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'role',
            'is_active', 'date_joined',
            'avatar', 'avatar_url', 'avatar_src'
        ]
        # ⚠️ on ne met PAS read_only_fields ici pour 'role'
        # car on veut le contrôler dynamiquement dans get_fields()

    def get_fields(self):
        """
        Rend 'role' éditable SEULEMENT pour un admin.
        'email', 'date_joined', 'is_active' restent toujours en lecture seule.
        """
        fields = super().get_fields()
        request = self.context.get('request')

        # Toujours RO
        for k in ('email', 'date_joined', 'is_active'):
            if k in fields:
                fields[k].read_only = True

        # Admin detection
        is_admin = False
        if request and request.user and request.user.is_authenticated:
            ru = request.user
            is_admin = (
                getattr(ru, 'is_staff', False)
                or getattr(ru, 'is_superuser', False)
                or str(getattr(ru, 'role', '')).lower() == 'admin'
            )

        # 'role' modifiable uniquement par admin
        if 'role' in fields and not is_admin:
            fields['role'].read_only = True

        return fields

    def get_avatar_src(self, obj):
        if getattr(obj, 'avatar', None):
            try:
                return self.context['request'].build_absolute_uri(obj.avatar.url)
            except Exception:
                return obj.avatar.url
        if getattr(obj, 'avatar_url', None):
            return obj.avatar_url
        return getattr(settings, 'DEFAULT_AVATAR_URL', None)

    def validate_username(self, v):
        if v is None:
            return v
        v = (v or "").strip().lower()
        if not USERNAME_RX.match(v):
            raise serializers.ValidationError("3–20 caractères, a-z 0-9 _ uniquement.")
        qs = User.objects.filter(username__iexact=v)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Nom d'utilisateur déjà pris.")
        return v

    def validate_avatar(self, img):
        if not img:
            return img
        if img.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image trop lourde (max 5 Mo).")
        return img

    def validate(self, attrs):
        if 'avatar_url' in attrs and attrs.get('avatar_url') == '':
            attrs['avatar_url'] = None
        return attrs

    def update(self, instance, validated_data):
        """
        On conserve ta logique existante, avec rôle désormais modifiable
        (si l’admin l’a envoyé et qu’il est autorisé par Model.choices).
        """
        new_file = validated_data.pop('avatar', serializers.empty)
        new_url = validated_data.pop('avatar_url', serializers.empty)

        for k, v in validated_data.items():
            setattr(instance, k, v)

        if new_file is not serializers.empty:
            instance.avatar = new_file
            instance.avatar_url = None
        elif new_url is not serializers.empty:
            instance.avatar_url = new_url or None
            if new_url:
                instance.avatar = None

        instance.full_clean(exclude=['password'])
        instance.save()
        return instance
