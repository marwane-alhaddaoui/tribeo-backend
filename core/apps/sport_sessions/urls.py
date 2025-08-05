from django.urls import path
from sport_sessions.views.list_create_view import SessionListCreateView
from sport_sessions.views.join_session_view import JoinSessionView
from sport_sessions.views.leave_session_view import LeaveSessionView

urlpatterns = [
    path('', SessionListCreateView.as_view(), name='sessions-list-create'),
    path('<int:pk>/join/', JoinSessionView.as_view(), name='join-session'),
    path('<int:pk>/leave/', LeaveSessionView.as_view(), name='leave-session'),
]
