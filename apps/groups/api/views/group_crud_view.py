# apps/groups/api/views/group_crud_view.py
from django.db.models import Count, Q
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from apps.groups.models import Group, GroupMember
from apps.groups.api.serializers.group_serializer import GroupListSerializer, GroupDetailSerializer
from apps.groups.api.permissions.group_permissions import IsGroupOwnerOrManager, CanCreateGroup

class GroupListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, CanCreateGroup]

    def get_queryset(self):
        u = self.request.user if self.request.user.is_authenticated else None
        qs = Group.objects.all().annotate(members_count=Count("memberships"))

        # Filtres optionnels
        sport_id = self.request.query_params.get("sport")
        if sport_id:
            qs = qs.filter(sport_id=sport_id)
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__icontains=city)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

        # Visibilité de la liste
        base = Q(group_type=Group.GroupType.OPEN) | Q(group_type=Group.GroupType.PRIVATE)
        if u:
            base |= Q(owner=u) | Q(memberships__user=u, memberships__status=GroupMember.STATUS_ACTIVE)
        return qs.filter(base).distinct()

    def get_serializer_class(self):
        return GroupListSerializer if self.request.method == "GET" else GroupDetailSerializer

    def perform_create(self, serializer):
        group = serializer.save(owner=self.request.user)
        GroupMember.objects.get_or_create(
            group=group, user=self.request.user,
            defaults={"role": GroupMember.ROLE_OWNER, "status": GroupMember.STATUS_ACTIVE}
        )

class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupOwnerOrManager]

    def get_queryset(self):
        u = self.request.user
        allowed = (
            Q(group_type=Group.GroupType.OPEN) |
            Q(owner=u) |
            Q(memberships__user=u, memberships__status=GroupMember.STATUS_ACTIVE)
        )
        return Group.objects.filter(allowed).distinct()

    def perform_destroy(self, instance):
        is_owner = (instance.owner_id == self.request.user.id)
        is_admin = getattr(self.request.user, "is_superuser", False) or getattr(self.request.user, "is_staff", False)
        if not (is_owner or is_admin):
            raise PermissionDenied("Only the group owner or an admin can delete this group.")
        instance.delete()
