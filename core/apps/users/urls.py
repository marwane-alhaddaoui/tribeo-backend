from django.urls import path
from users.views.auth_views import RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
]
