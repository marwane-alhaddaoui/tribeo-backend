from rest_framework import generics
from apps.users.models import CustomUser
from apps.users.api.serializers.user_serializer import UserSerializer
from apps.users.api.permissions.roles_permissions import IsAdmin


class AdminUserListView(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]