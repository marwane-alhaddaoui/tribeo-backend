from django.urls import path
from apps.sport_sessions.api.views.list_create_view import SessionListCreateView
from apps.sport_sessions.api.views.join_session_view import JoinSessionView
from apps.sport_sessions.api.views.leave_session_view import LeaveSessionView
from apps.sport_sessions.api.views.detail_session_view import SessionDetailView

urlpatterns = [
    path('', SessionListCreateView.as_view(), name='sessions-list-create'),
    path('<int:pk>/', SessionDetailView.as_view(), name='session-detail'),
    path('<int:pk>/join/', JoinSessionView.as_view(), name='join-session'),
    path('<int:pk>/leave/', LeaveSessionView.as_view(), name='leave-session'),
    
]
