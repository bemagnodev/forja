from unittest.mock import patch
import pytest


@pytest.mark.django_db
@patch('api.services.scrapers.atcoder.AtCoderScraper.scrape')
@patch('api.services.atcoder_client.AtCoderClient.get_problems')
def test_sync_atcoder_endpoint(mock_get_problems, mock_scrape, api_client, base_user):
    """Testa o endpoint POST /api/sync/atcoder usando mocks para clientes externos."""
    mock_get_problems.return_value = [
        {"id": "abc100_a", "contest_id": "abc100", "title": "Happy New Year", "name": "Happy New Year"}
    ]
    
    mock_scrape.return_value = {
        "user_handle": "mentor_ac",
        "submissions": [
            {
                "submission_id": "ac_sub_1",
                "problem_id": "abc100_a",
                "contest_id": "abc100",
                "verdict": "AC",
                "creation_time": 1600000000,
            }
        ]
    }
    
    resp = api_client.post("/api/sync/atcoder")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.django_db
def test_sync_atcoder_api(api_client, base_user):
    """Testa o endpoint de disparo de sync do AtCoder quando o usuário possui atcoder_handle."""
    base_user.atcoder_handle = "tourist"
    base_user.save()
    
    resp = api_client.post("/api/sync/atcoder")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["handle"] == "tourist"
