import pytest
from django.urls import reverse
from api.models import User


@pytest.mark.django_db
def test_login_returns_access_and_refresh_tokens_for_valid_credentials(client):
    user = User.objects.create_user(
        username="login_valido",
        password="SenhaValida123!",
        is_active=True,
    )

    response = client.post(
        reverse("api:token_obtain_pair"),
        data={
            "username": user.username,
            "password": "SenhaValida123!",
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access"]
    assert data["refresh"]
    assert "password" not in data


@pytest.mark.django_db
def test_login_rejects_invalid_password_without_issuing_tokens(client):
    user = User.objects.create_user(
        username="login_invalido",
        password="SenhaCorreta123!",
        is_active=True,
    )

    response = client.post(
        reverse("api:token_obtain_pair"),
        data={
            "username": user.username,
            "password": "SenhaErrada123!",
        },
        content_type="application/json",
    )

    assert response.status_code == 401
    data = response.json()
    assert "access" not in data
    assert "refresh" not in data

    user.refresh_from_db()
    assert user.check_password("SenhaCorreta123!")


@pytest.mark.django_db
def test_login_rejects_inactive_user_without_issuing_tokens(client):
    user = User.objects.create_user(
        username="login_inativo",
        password="SenhaValida123!",
        is_active=False,
    )

    response = client.post(
        reverse("api:token_obtain_pair"),
        data={
            "username": user.username,
            "password": "SenhaValida123!",
        },
        content_type="application/json",
    )

    assert response.status_code == 401
    data = response.json()
    assert "access" not in data
    assert "refresh" not in data

    user.refresh_from_db()
    assert user.is_active is False
    assert user.check_password("SenhaValida123!")
