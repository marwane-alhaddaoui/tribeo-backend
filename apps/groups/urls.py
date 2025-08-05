from django.urls import path
from apps.groups.api.views.group_crud_view import GroupListCreateView, GroupDetailView
from apps.groups.api.views.group_join_leave_view import JoinGroupView, LeaveGroupView

urlpatterns = [
    path('', GroupListCreateView.as_view(), name='list_create_group'),
    path('<int:pk>/', GroupDetailView.as_view(), name='detail_group'),
    path('<int:pk>/join/', JoinGroupView.as_view(), name='join_group'),
    path('<int:pk>/leave/', LeaveGroupView.as_view(), name='leave_group'),
]
