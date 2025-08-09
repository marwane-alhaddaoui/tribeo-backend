from django.urls import path
from apps.sport_sessions.api.views.list_create_view import SessionListCreateView
from apps.sport_sessions.api.views.join_session_view import JoinSessionView
from apps.sport_sessions.api.views.leave_session_view import LeaveSessionView
from apps.sport_sessions.api.views.detail_session_view import SessionDetailView
from apps.sport_sessions.api.views.admin_views import AdminSessionListView, AdminSessionDetailView

urlpatterns = [
    path('', SessionListCreateView.as_view(), name='list_create_session'),
    path('<int:pk>/', SessionDetailView.as_view(), name='detail_session'),
    path('<int:pk>/join/', JoinSessionView.as_view(), name='join_session'),
    path('<int:pk>/leave/', LeaveSessionView.as_view(), name='leave_session'),
    # Admin
    path('admin/sessions/', AdminSessionListView.as_view(), name='admin-sessions'),
    path('admin/sessions/<int:pk>/', AdminSessionDetailView.as_view(), name='admin-session-detail'),

]
