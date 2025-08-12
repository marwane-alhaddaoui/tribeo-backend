from rest_framework import generics, permissions
from django.db.models import Count
from apps.groups.models import Group, GroupMember
from apps.groups.api.serializers.group_serializer import GroupListSerializer, GroupDetailSerializer
from apps.groups.api.permissions.group_permissions import IsGroupOwnerOrManager

class GroupListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Group.objects.all().annotate(
            members_count=Count("memberships", filter=None)
        )
        # Si tu veux : filtrer par sport / ville / q
        sport_id = self.request.query_params.get("sport")
        if sport_id:
            qs = qs.filter(sport_id=sport_id)
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__icontains=city)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_serializer_class(self):
        # liste => list serializer
        if self.request.method == "GET":
            return GroupListSerializer
        # création => detail (on renvoie l’objet complet créé)
        return GroupDetailSerializer

    def perform_create(self, serializer):
        group = serializer.save(owner=self.request.user)
        # auto-membership owner
        GroupMember.objects.get_or_create(
            group=group, user=self.request.user,
            defaults={"role": GroupMember.ROLE_OWNER, "status": GroupMember.STATUS_ACTIVE}
        )


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupDetailSerializer
    permission_classes = [IsGroupOwnerOrManager]
