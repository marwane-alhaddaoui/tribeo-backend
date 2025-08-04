from django.urls import path
from sport_sessions.views.sport_session_views import SessionListCreateView

urlpatterns = [
    path('', SessionListCreateView.as_view(), name='sessions-list-create'),
]
