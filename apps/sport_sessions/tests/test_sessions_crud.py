import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models.users import CustomUser

@pytest.mark.django_db
def test_create_and_list_sessions():
    client = APIClient()
    user = CustomUser.objects.create_user(
        email="creator@example.com",
        first_name="Creator",
        last_name="One",
        password="password123",
        role="coach"   # coach autorisé à créer session privée ou publique
    )
    client.force_authenticate(user=user)

    # Create session
    response = client.post(reverse('list_create_session'), {
        "title": "Foot du samedi",
        "sport": "football",           
        "date": "2025-08-20",
        "start_time": "15:00",
        "location": "Paris",
        "max_players": 10,
        "team_mode": False,
        "is_public": True
    })
    assert response.status_code == 201, f"Expected 201, got {response.status_code}, data: {response.data}"
    session_id = response.data['id']

    # List sessions
    response = client.get(reverse('list_create_session'))
    assert response.status_code == 200
    assert any(s["id"] == session_id for s in response.data), "Session not found in list"

    # Get session detail
    response = client.get(reverse('detail_session', args=[session_id]))
    assert response.status_code == 200
    assert response.data["title"] == "Foot du samedi"
    assert response.data["max_players"] == 10
    assert response.data["is_public"] is True
