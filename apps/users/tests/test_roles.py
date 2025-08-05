import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models import CustomUser

@pytest.mark.django_db
def test_register_with_role():
    client = APIClient()

    response = client.post(reverse('register'), {
        "email": "coach@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "testpass123",
        "role": "coach"
    })
    assert response.status_code == 201
    assert CustomUser.objects.get(email="coach@example.com").role == "coach"

@pytest.mark.django_db
def test_register_default_role_user():
    client = APIClient()

    response = client.post(reverse('register'), {
        "email": "player@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "password": "testpass123"
    })
    assert response.status_code == 201
    assert CustomUser.objects.get(email="player@example.com").role == "user"

@pytest.mark.django_db
def test_profile_returns_role():
    client = APIClient()
    user = CustomUser.objects.create_user(
        email="admin@example.com",
        first_name="Admin",
        last_name="Test",
        password="password123",
        role="admin"
    )
    client.force_authenticate(user=user)

    response = client.get(reverse('profile'))
    assert response.status_code == 200
    assert response.data["role"] == "admin"
