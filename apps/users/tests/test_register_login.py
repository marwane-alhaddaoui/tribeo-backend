import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models.users import CustomUser

@pytest.mark.django_db
def test_register_and_login():
    client = APIClient()

    # Register
    response = client.post(reverse('register'), {
        "email": "testuser@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "testpassword123"
    })
    assert response.status_code == 201

    # Login
    response = client.post(reverse('login'), {
        "email": "testuser@example.com",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    assert "access" in response.data

@pytest.mark.django_db
def test_register_duplicate_email_fails():
    client = APIClient()
    CustomUser.objects.create_user(
        email="duplicate@example.com",
        first_name="Dup",
        last_name="User",
        password="pass1234"
    )

    response = client.post(reverse('register'), {
        "email": "duplicate@example.com",
        "first_name": "Dup",
        "last_name": "User",
        "password": "pass1234"
    })
    assert response.status_code == 400
