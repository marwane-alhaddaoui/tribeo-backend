from django.urls import path
from apps.groups.api.views.group_crud_view import (
    GroupListCreateView, GroupDetailView)
from apps.groups.api.views.group_join_leave_view import (
    JoinGroupView, LeaveGroupView)
from apps.groups.api.views.group_member_views import (
    AddMemberView, RemoveMemberView)
from apps.groups.api.views.group_requests_views import (
    ListJoinRequestsView, ApproveJoinRequestView, RejectJoinRequestView)
from apps.groups.api.views.group_external_member_views import (
    ExternalMemberListCreateView, ExternalMemberDeleteView)
from apps.sport_sessions.api.views.attendance_view import SessionAttendanceView

urlpatterns = [
    # CRUD
    path('',                         GroupListCreateView.as_view(),  name='list_create_group'),
    path('<int:pk>/',                GroupDetailView.as_view(),      name='detail_group'),

    # Join / Leave
    path('<int:pk>/join/',           JoinGroupView.as_view(),        name='join_group'),
    path('<int:pk>/leave/',          LeaveGroupView.as_view(),       name='leave_group'),

    # Members (owner only)
    path('<int:pk>/add-member/',     AddMemberView.as_view(),        name='add_member'),
    path('<int:pk>/remove-member/',  RemoveMemberView.as_view(),     name='remove_member'),

    # Join Requests (owner only)
    path('<int:pk>/requests/',                       ListJoinRequestsView.as_view(),   name='group_requests'),
    path('<int:pk>/requests/<int:rid>/approve/',     ApproveJoinRequestView.as_view(), name='group_requests_approve'),
    path('<int:pk>/requests/<int:rid>/reject/',      RejectJoinRequestView.as_view(),  name='group_requests_reject'),

    # External Members (owner only)
    path('<int:pk>/external-members/',               ExternalMemberListCreateView.as_view(), name='group_external_list_create'),
    path('external-members/<int:eid>/',              ExternalMemberDeleteView.as_view(),     name='group_external_delete'),

    path('<int:gid>/trainings/<int:pk>/attendance/', SessionAttendanceView.as_view(), name='group-training-attendance'),

]
