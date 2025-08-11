# apps/users/api/views/admin_views.py
from rest_framework import generics, permissions
from django.contrib.auth import get_user_model
from apps.users.api.serializers.user_serializer import RegisterSerializer, UserSerializer
from apps.users.api.permissions.roles_permissions import IsAdmin

User = get_user_model()

class AdminUserListView(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by('-date_joined')
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        # GET -> liste: UserSerializer (lecture)
        # POST -> création: RegisterSerializer (gère password + username)
        return RegisterSerializer if self.request.method == 'POST' else UserSerializer


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
