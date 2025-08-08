from rest_framework import generics
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers import SessionSerializer
from apps.users.api.permissions.roles_permissions import IsAdmin

class AdminSessionListView(generics.ListAPIView):
    queryset = SportSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAdmin]
