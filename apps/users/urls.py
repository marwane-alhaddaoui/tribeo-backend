# urls.py (users)
from django.urls import path
from apps.users.api.views.auth_views import RegisterView, LoginView, MeView
from rest_framework_simplejwt.views import TokenRefreshView
from apps.users.api.views.admin_views import AdminUserListView, AdminUserDetailView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),                  # ← custom (email ou username)
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', MeView.as_view(), name='profile'),                 # ← remplace ProfileView
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
]
