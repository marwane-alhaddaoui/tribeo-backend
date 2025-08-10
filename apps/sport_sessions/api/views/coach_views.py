from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.sport_sessions.models import SportSession

class IsCoachOrOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: SportSession):
        if not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False):
            return True
        if getattr(request.user, "is_coach", False):
            return obj.creator_id == request.user.id
        return obj.creator_id == request.user.id

class PublishSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCoachOrOwner]
    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)
        self.check_object_permissions(request, session)
        session.status = SportSession.Status.OPEN
        session.save(update_fields=["status"])
        return Response({"status": session.status})

class LockSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCoachOrOwner]
    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)
        self.check_object_permissions(request, session)
        session.status = SportSession.Status.LOCKED
        session.save(update_fields=["status"])
        return Response({"status": session.status})

class ScoreSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCoachOrOwner]
    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)
        self.check_object_permissions(request, session)
        session.score_home = request.data.get("score_home")
        session.score_away = request.data.get("score_away")
        session.status = SportSession.Status.FINISHED
        session.save(update_fields=["score_home", "score_away", "status"])
        return Response({
            "status": session.status,
            "score_home": session.score_home,
            "score_away": session.score_away
        })

class CancelSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCoachOrOwner]
    def post(self, request, pk):
        session = get_object_or_404(SportSession, pk=pk)
        self.check_object_permissions(request, session)
        session.status = SportSession.Status.CANCELED
        session.save(update_fields=["status"])
        return Response({"status": session.status})
