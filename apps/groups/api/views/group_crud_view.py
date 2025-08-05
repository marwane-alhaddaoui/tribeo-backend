from rest_framework import generics, permissions
from apps.groups.models.group import Group
from apps.groups.api.serializers.group_serializer import GroupSerializer
from apps.groups.api.permissions.group_permissions import IsCoachOrAdmin

class GroupListCreateView(generics.ListCreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsCoachOrAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(coach=self.request.user)


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsCoachOrAdmin]
