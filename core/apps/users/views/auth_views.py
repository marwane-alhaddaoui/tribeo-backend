from rest_framework import generics
from users.models import CustomUser
from users.serializers.user_serializer import RegisterSerializer

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = []  # Accessible sans être connecté
