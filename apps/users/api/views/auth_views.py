# apps/users/api/views/auth_views.py
from rest_framework import generics, permissions, serializers,status
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.users.api.serializers.user_serializer import RegisterSerializer, UserSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from apps.audit.utils import audit_log
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'register'
    throttle_classes = [ScopedRateThrottle]
    
    def perform_create(self, serializer):
        user = serializer.save()
        try:
            audit_log(self.request, "user.register", obj=user)
        except Exception:
            pass


# ---- Login: email OU username, + extra claims ----
class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD  # 'email' dans ton modèle

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # rendre email non requis et ajouter un champ username
        if self.username_field in self.fields:
            self.fields[self.username_field].required = False
        self.fields['username'] = serializers.CharField(required=False)

    def validate(self, attrs):
        identifier = attrs.get('username') or attrs.get('email') or attrs.get(self.username_field)
        password = attrs.get('password')

        if not identifier or not password:
            raise serializers.ValidationError({"detail": "Missing credentials."})

        # Recherche de l'utilisateur par email ou username
        try:
            if '@' in identifier:
                user_obj = User.objects.get(email__iexact=identifier.strip())
            else:
                user_obj = User.objects.get(username__iexact=identifier.strip().lower())
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "No active account found."})

        # Authentification avec USERNAME_FIELD (email chez toi)
        user = authenticate(**{User.USERNAME_FIELD: user_obj.email}, password=password)
        if not user:
            raise serializers.ValidationError({"detail": "No active account found."})

        # Laisse SimpleJWT gérer la génération du token
        data = super().validate({self.username_field: user.email, "password": password})
        try:
            audit_log(self.context.get("request"), "user.login", actor=user)
        except Exception:
            pass
        # Ajoute les infos utilisateur dans la réponse
        data['user'] = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
        }
        return data


class LoginView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer
    throttle_scope = 'login'
    throttle_classes = [ScopedRateThrottle]


class RefreshView(TokenRefreshView):
    pass


class MeView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    parser_classes = [MultiPartParser, FormParser]  # JSON reste supporté par défaut
    def get_object(self): return self.request.user
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        # Désactivation + anonymisation minimale (RGPD-friendly) sans casser les FKs
        user.is_active = False
        try:
            uid = str(user.id or "").strip()
        except Exception:
            uid = ""
        # Username: <=20 chars, regex [a-z0-9_]
        new_username = (f"deleted_{uid}" if uid else f"deleted_{user.pk}")[:20].lower()
        if new_username and new_username != user.username:
            user.username = new_username
        # Email: alias unique non nominatif
        try:
            user.email = f"deleted+{user.pk}@deleted.local"
        except Exception:
            pass
        # PII visibles
        if hasattr(user, "first_name"): user.first_name = ""
        if hasattr(user, "last_name"): user.last_name = ""
        if hasattr(user, "avatar"): user.avatar = None
        if hasattr(user, "avatar_url"): user.avatar_url = None
        user.save(update_fields=[
            "is_active","username","email","first_name","last_name","avatar","avatar_url"
        ])
        try:
            audit_log(request, "user.deactivate_self", actor=user)
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


