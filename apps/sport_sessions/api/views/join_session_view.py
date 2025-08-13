from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.sport_sessions.models import SportSession
from apps.sport_sessions.api.serializers.session_serializer import SessionSerializer
from apps.groups.models import GroupMember  # NEW

class JoinSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)

        # 🔒 sessions de groupe : réservé aux membres actifs du groupe
        if session.visibility == SportSession.Visibility.GROUP and session.group_id:
            is_member = GroupMember.objects.filter(
                group=session.group, user=request.user,
                status=GroupMember.STATUS_ACTIVE
            ).exists()
            if not is_member:
                return Response({"detail": "Accès réservé aux membres du groupe."}, status=status.HTTP_403_FORBIDDEN)

        # déjà inscrit ?
        if session.participants.filter(id=request.user.id).exists():
            return Response(SessionSerializer(session).data, status=status.HTTP_200_OK)

        # capacité pleine ?
        if session.is_full():
            return Response({"detail": "La session est complète."}, status=status.HTTP_400_BAD_REQUEST)

        session.participants.add(request.user)
        session.save()
        return Response(SessionSerializer(session).data, status=status.HTTP_200_OK)
