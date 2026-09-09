from unittest.mock import patch
import pytest


@pytest.mark.django_db
@patch("api.api.dispatch_sync")
def test_sync_atcoder_endpoint_dispatches_background_task(mock_dispatch, api_client, base_user):
    """Testa se POST /api/sync/atcoder chama o dispatch_sync com o comando e handle corretos sem rodar thread real."""
    base_user.atcoder_handle = "tourist"
    base_user.save()

    resp = api_client.post("/api/sync/atcoder")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["handle"] == "tourist"
    mock_dispatch.assert_called_once_with("sync_atcoder", "tourist")


@pytest.mark.django_db
@patch("api.api.dispatch_sync")
def test_sync_codeforces_endpoint_dispatches_background_task(mock_dispatch, api_client, base_user):
    """Testa se POST /api/sync/cf chama o dispatch_sync com o comando e handle corretos sem rodar thread real."""
    base_user.cf_handle = "tourist"
    base_user.save()

    resp = api_client.post("/api/sync/cf")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["handle"] == "tourist"
    mock_dispatch.assert_called_once_with("sync_cf", "tourist")


@pytest.mark.django_db
@patch("api.api.dispatch_sync")
def test_sync_atcoder_endpoint_without_handle(mock_dispatch, api_client, base_user):
    """Testa se POST /api/sync/atcoder retorna mensagem informando falta de handle e não chama dispatch_sync."""
    base_user.atcoder_handle = ""
    base_user.save()

    resp = api_client.post("/api/sync/atcoder")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "Nenhum handle configurado" in data["message"]
    mock_dispatch.assert_not_called()


@pytest.mark.django_db
@patch("api.api.dispatch_sync")
def test_sync_codeforces_endpoint_without_handle(mock_dispatch, api_client, base_user):
    """Testa se POST /api/sync/cf retorna mensagem informando falta de handle e não chama dispatch_sync."""
    base_user.cf_handle = ""
    base_user.save()

    resp = api_client.post("/api/sync/cf")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "Nenhum handle configurado" in data["message"]
    mock_dispatch.assert_not_called()
