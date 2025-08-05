from django.urls import path
from sport_sessions.views.list_create_view import SessionListCreateView
from sport_sessions.views.join_leave_view import JoinSessionView

urlpatterns = [
    path('', SessionListCreateView.as_view(), name='sessions-list-create'),
    path('<int:pk>/join/', JoinSessionView.as_view(), name='join-session'),
]
