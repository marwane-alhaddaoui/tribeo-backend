import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models.users import CustomUser
from apps.groups.models.group import Group

@pytest.mark.django_db
def test_coach_can_create_and_join_group():
    client = APIClient()
    coach = CustomUser.objects.create_user(
        email="coach@example.com",
        first_name="Coach",
        last_name="User",
        password="pass123",
        role="coach"
    )
    client.force_authenticate(user=coach)

    # Création du groupe
    response = client.post(reverse('list_create_group'), {
        "name": "Team Alpha",
        "description": "Premier groupe test"
    })
    assert response.status_code == 201
    group_id = response.data['id']

    # Join group
    response = client.post(reverse('join_group', args=[group_id]))
    assert response.status_code == 200
    assert any(m == coach.email for m in response.data['members'])
