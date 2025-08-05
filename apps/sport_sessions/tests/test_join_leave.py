import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models.users import CustomUser
from apps.sport_sessions.models.sport_session import SportSession

@pytest.mark.django_db
def test_join_and_leave_session():
    client = APIClient()
    user = CustomUser.objects.create_user(
        email="player@example.com",
        first_name="Player",
        last_name="One",
        password="password123"
    )
    session = SportSession.objects.create(
    title="Match amical",
    sport="football",
    date="2025-08-21",
    location="Marseille",
    start_time="15:00",
    max_participants=10,
    creator=user
)
    client.force_authenticate(user=user)

    # Join
    response = client.post(reverse('join_session', args=[session.id]))
    assert response.status_code == 200

    # Leave
    response = client.post(reverse('leave_session', args=[session.id]))
    assert response.status_code == 200
