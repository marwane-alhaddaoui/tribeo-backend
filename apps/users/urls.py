from django.urls import path
from apps.users.api.views.auth_views import RegisterView,LoginView, ProfileView
from rest_framework_simplejwt.views import TokenRefreshView
from apps.users.api.views.admin_views import AdminUserListView,AdminUserDetailView


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
     # 🔹 Liste de tous les users (admin only)
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
]
