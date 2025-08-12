# apps/users/urls.py
from django.urls import path
from apps.users.api.views.auth_views import RegisterView, LoginView, MeView
from rest_framework_simplejwt.views import TokenRefreshView
from apps.users.api.views.admin_views import AdminUserListView, AdminUserDetailView
from apps.users.api.views.user_search_view import UserSearchView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', MeView.as_view(), name='profile'),

    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),

    # ✅ CORRECT: pas de "users/" ici, le préfixe est déjà dans config/urls.py
    path('search/', UserSearchView.as_view(), name='user-search'),
]
  