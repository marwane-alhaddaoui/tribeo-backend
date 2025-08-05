import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models.users import CustomUser
from apps.sport_sessions.models.sport_session import SportSession
from apps.teams.models.team import Team

@pytest.mark.django_db
def test_create_team_and_join():
    client = APIClient()
    coach = CustomUser.objects.create_user(
        email="coach@example.com",
        first_name="Coach",
        last_name="User",
        password="pass123",
        role="coach"
    )
    session = SportSession.objects.create(
        title="Match foot",
        sport="football",
        date="2025-08-20",
        start_time="10:00",
        location="Paris",
        max_players=10,
        is_public=True,
        team_mode=True,
        creator=coach
    )
    client.force_authenticate(user=coach)

    # Création d'une équipe
    response = client.post(reverse('list_create_team', args=[session.id]), {
        "name": "Les rouges",
        "color": "red"
    })
    assert response.status_code == 201
    team_id = response.data['id']

    # Join team
    response = client.post(reverse('join_team', args=[team_id]))
    assert response.status_code == 200
    assert any(m == coach.email for m in response.data['members'])
