# apps/users/api/serializers/user_serializer.py
from django.conf import settings
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
    # 🆕 avatar fichier OU URL + source finale calculée
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
        # Email/role non éditables depuis /auth/profile/
        read_only_fields = ['email', 'date_joined', 'is_active', 'role']

    def get_avatar_src(self, obj):
        """
        URL finale à utiliser côté front :
        1) fichier uploadé (URL absolue)
        2) avatar_url (URL fournie)
        3) DEFAULT_AVATAR_URL (logo par défaut)
        """
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
        # ~5 Mo max
        if img.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image trop lourde (max 5 Mo).")
        # content_type peut être absent selon le storage ; on ne bloque pas fort ici
        return img

    def validate(self, attrs):
        """
        Harmonisation:
        - avatar_url='' => None (efface)
        """
        if 'avatar_url' in attrs and attrs.get('avatar_url') == '':
            attrs['avatar_url'] = None
        return attrs

    def update(self, instance, validated_data):
        """
        Règles:
        - Si 'avatar' (fichier) fourni -> on set le fichier et on clear avatar_url
        - Si 'avatar_url' fourni (non vide) -> on set l'URL et on clear le fichier
        - Si les deux sont absents -> on met juste à jour les autres champs
        """
        new_file = validated_data.pop('avatar', serializers.empty)
        new_url = validated_data.pop('avatar_url', serializers.empty)

        # autres champs (username, first_name, last_name, ...)
        for k, v in validated_data.items():
            setattr(instance, k, v)

        if new_file is not serializers.empty:
            instance.avatar = new_file
            instance.avatar_url = None
        elif new_url is not serializers.empty:
            instance.avatar_url = new_url or None
            if new_url:  # si on a défini une URL, on enlève l'ancien fichier
                instance.avatar = None

        instance.full_clean(exclude=['password'])
        instance.save()
        return instance
