from rest_framework import generics
from apps.users.models import CustomUser
from apps.users.api.serializers.user_serializer import RegisterSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = RegisterSerializer(request.user)
        return Response(serializer.data)
