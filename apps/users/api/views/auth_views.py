# apps/users/api/views/auth_views.py
from rest_framework import generics, permissions, serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.users.api.serializers.user_serializer import RegisterSerializer, UserSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


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


class RefreshView(TokenRefreshView):
    pass


# ---- /auth/me : GET & PUT/PATCH ----
class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
