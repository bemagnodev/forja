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
@patch("api.api.start_cf_sync", return_value={'state': 'running', 'run_id': 'run-one', 'message': 'Sincronização iniciada.'})
def test_sync_codeforces_endpoint_dispatches_background_task(mock_dispatch, api_client, base_user):
    """Testa se POST /api/sync/cf chama o dispatch_sync com o comando e handle corretos sem rodar thread real."""
    base_user.cf_handle = "tourist"
    base_user.save()

    resp = api_client.post("/api/sync/cf")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["handle"] == "tourist"
    assert data['state'] == 'running'
    assert data['run_id'] == 'run-one'
    mock_dispatch.assert_called_once_with("tourist")


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
@patch("api.api.start_cf_sync")
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


@pytest.mark.django_db
@patch('api.api.start_cf_sync', return_value={'state': 'busy', 'message': 'Aguarde.'})
def test_cf_sync_busy_is_not_reported_as_started(start, api_client):
    response = api_client.post('/api/sync/cf')
    assert response.status_code == 200
    assert response.json()['success'] is False
    assert response.json()['state'] == 'busy'


@pytest.mark.django_db
@patch('api.api.read_cf_sync', return_value={'state': 'completed', 'message': 'Concluída.'})
def test_cf_sync_status_is_scoped_to_authenticated_handle(read, api_client, base_user):
    response = api_client.get('/api/sync/cf/status?run_id=run-one')
    assert response.status_code == 200
    assert response.json()['state'] == 'completed'
    read.assert_called_once_with(base_user.cf_handle, 'run-one')
