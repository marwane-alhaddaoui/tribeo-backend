from rest_framework import generics
from users.models import CustomUser
from users.serializers.user_serializer import RegisterSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = []  # Accessible sans être connecté
    
    
class LoginView(TokenObtainPairView):
    """
    POST: /api/auth/login/
    Body: {"email": "user@test.com", "password": "password123"}
    """
    pass