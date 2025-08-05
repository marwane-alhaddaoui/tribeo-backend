import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models import CustomUser

@pytest.mark.django_db
def test_only_admin_or_coach_can_create_session():
    client = APIClient()

    # User normal
    user = CustomUser.objects.create_user(
        email="normal@example.com",
        first_name="Norm",
        last_name="User",
        password="pass123",
        role="user"
    )
    client.force_authenticate(user=user)
    response = client.post(reverse('list_create_session'), {
        "title": "Test Match",
        "sport": "football",
        "date": "2025-08-20",
        "start_time": "10:00",
        "location": "Paris"
    })
    assert response.status_code == 403

    # Coach
    coach = CustomUser.objects.create_user(
        email="coach@example.com",
        first_name="Coach",
        last_name="User",
        password="pass123",
        role="coach"
    )
    client.force_authenticate(user=coach)
    response = client.post(reverse('list_create_session'), {
        "title": "Coach Match",
        "sport": "football",
        "date": "2025-08-20",
        "start_time": "10:00",
        "location": "Paris"
    })
    assert response.status_code == 201
