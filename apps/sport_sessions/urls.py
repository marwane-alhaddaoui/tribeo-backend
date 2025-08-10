from django.urls import path
from apps.sport_sessions.api.views.list_create_view import SessionListCreateView
from apps.sport_sessions.api.views.join_session_view import JoinSessionView
from apps.sport_sessions.api.views.leave_session_view import LeaveSessionView
from apps.sport_sessions.api.views.detail_session_view import SessionDetailView
from apps.sport_sessions.api.views.admin_views import AdminSessionListView, AdminSessionDetailView
from apps.sport_sessions.api.views import coach_views


urlpatterns = [
    path('', SessionListCreateView.as_view(), name='list_create_session'),
    path('<int:pk>/', SessionDetailView.as_view(), name='detail_session'),
    path('<int:pk>/join/', JoinSessionView.as_view(), name='join_session'),
    path('<int:pk>/leave/', LeaveSessionView.as_view(), name='leave_session'),
    # Admin
    path('admin/sessions/', AdminSessionListView.as_view(), name='admin-sessions'),
    path('admin/sessions/<int:pk>/', AdminSessionDetailView.as_view(), name='admin-session-detail'),

    # Coach actions
    path('<int:pk>/publish/', coach_views.PublishSessionView.as_view(), name='publish_session'),
    path('<int:pk>/lock/', coach_views.LockSessionView.as_view(), name='lock_session'),
    path('<int:pk>/score/', coach_views.ScoreSessionView.as_view(), name='score_session'),
    path('<int:pk>/cancel/', coach_views.CancelSessionView.as_view(), name='cancel_session'),
]
