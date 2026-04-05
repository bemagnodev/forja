import pytest
import responses
import requests
from api.services.codeforces_client import CodeforcesClient
from api.services.atcoder_client import AtCoderClient

@responses.activate
def test_codeforces_client_success():
    client = CodeforcesClient(sleep_time=0)
    
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={'status': 'OK', 'result': [{'id': 12345, 'verdict': 'OK'}]},
        status=200,
        match=[responses.matchers.query_param_matcher({'handle': 'toro', 'from': 1, 'count': 10})]
    )
    
    data = client.get_user_submissions('toro', from_idx=1, count=10)
    assert data is not None
    assert len(data) == 1
    assert data[0]['id'] == 12345

@responses.activate
def test_codeforces_client_api_error_returns_none():
    client = CodeforcesClient(sleep_time=0)
    
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.list',
        json={'status': 'FAILED', 'comment': 'Internal server error'},
        status=500
    )
    
    data = client.get_contests()
    # get_contests faz: return result if result else []
    assert data == []

@responses.activate
def test_atcoder_client_timeout():
    client = AtCoderClient(timeout=1, sleep_time=0)
    
    responses.add(
        responses.GET,
        'https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions',
        body=requests.exceptions.Timeout("Read timeout"),
    )
    
    data = client.get_user_submissions('toro')
    # O cliente Kenkoooo intercepta e retorna [] para fallback
    assert data == []
