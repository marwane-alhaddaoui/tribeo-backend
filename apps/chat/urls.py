# apps/chat/urls.py
from django.urls import path
from apps.chat.api.views.group_chat_views import (
    GroupChatListCreateView, GroupChatDeleteView
)
from apps.chat.api.views.session_chat_views import (
    SessionChatListCreateView, SessionChatDeleteView
)

urlpatterns = [
    # Groupe
    path('groups/<int:group_id>/chat/', GroupChatListCreateView.as_view(), name='group_chat_list_create'),
    path('groups/<int:group_id>/chat/<int:msg_id>/', GroupChatDeleteView.as_view(), name='group_chat_delete'),

    # Session
    path('sessions/<int:session_id>/chat/', SessionChatListCreateView.as_view(), name='session_chat_list_create'),
    path('sessions/<int:session_id>/chat/<int:msg_id>/', SessionChatDeleteView.as_view(), name='session_chat_delete'),
]
