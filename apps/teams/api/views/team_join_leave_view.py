from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.teams.models.team import Team
from apps.teams.api.serializers.team_serializer import TeamSerializer

class JoinTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)

        if team.members.filter(id=request.user.id).exists():
            return Response({"detail": "Vous êtes déjà dans cette équipe."},
                            status=status.HTTP_400_BAD_REQUEST)

        team.members.add(request.user)
        team.save()
        return Response(TeamSerializer(team).data, status=status.HTTP_200_OK)


class LeaveTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)

        if not team.members.filter(id=request.user.id).exists():
            return Response({"detail": "Vous n'êtes pas dans cette équipe."},
                            status=status.HTTP_400_BAD_REQUEST)

        team.members.remove(request.user)
        team.save()
        return Response(TeamSerializer(team).data, status=status.HTTP_200_OK)
