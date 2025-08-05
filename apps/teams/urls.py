from django.urls import path
from apps.teams.api.views.team_crud_view import TeamListCreateView, TeamDetailView
from apps.teams.api.views.team_join_leave_view import JoinTeamView, LeaveTeamView

urlpatterns = [
    path('session/<int:session_id>/', TeamListCreateView.as_view(), name='list_create_team'),
    path('<int:pk>/', TeamDetailView.as_view(), name='detail_team'),
    path('<int:pk>/join/', JoinTeamView.as_view(), name='join_team'),
    path('<int:pk>/leave/', LeaveTeamView.as_view(), name='leave_team'),
]
