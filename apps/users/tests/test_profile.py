import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models.users import CustomUser

@pytest.mark.django_db
def test_profile_requires_authentication():
    client = APIClient()
    response = client.get(reverse('profile'))
    assert response.status_code == 401

@pytest.mark.django_db
def test_profile_returns_user_data():
    client = APIClient()
    user = CustomUser.objects.create_user(
        email="profile@example.com",
        first_name="John",
        last_name="Doe",
        password="password123"
    )
    client.force_authenticate(user=user)

    response = client.get(reverse('profile'))
    assert response.status_code == 200
    assert response.data["email"] == "profile@example.com"
