import pytest
import responses
import requests
from api.services.codeforces_client import CodeforcesClient
from api.services.atcoder_client import AtCoderClient

@responses.activate
def test_codeforces_client_success():
    """
    Cenário: A API do Codeforces está online e responde corretamente ao pedido de submissões de um usuário.
    Resultado Esperado: O CodeforcesClient deve parsear o JSON e retornar exatamente a lista contida em 'result'.
    """
    client = CodeforcesClient(sleep_time=0, api_key="", api_secret="")
    
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
    """
    Cenário: A API do Codeforces retorna um código HTTP 500 (Erro no Servidor) e 'status' FAILED.
    Resultado Esperado: O cliente deve tratar o erro e retornar uma lista vazia, evitando que a pipeline de sincronismo lance exceções em cascata.
    """
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
    """
    Cenário: A API do Kenkoooo (AtCoder) trava e dá Timeout devido a lentidão na rede.
    Resultado Esperado: A biblioteca 'requests' vai engatilhar o erro Timeout, o AtCoderClient deve capturar isso (dentro de _make_request) e retornar lista vazia.
    """
    client = AtCoderClient(timeout=1, sleep_time=0)
    
    responses.add(
        responses.GET,
        'https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions',
        body=requests.exceptions.Timeout("Read timeout"),
    )
    
    data = client.get_user_submissions('toro')
    # O cliente Kenkoooo intercepta e retorna [] para fallback
    assert data == []

@responses.activate
def test_codeforces_client_timeout():
    """
    Cenário: A API do Codeforces demora muito a responder e gera Timeout.
    Resultado Esperado: Assim como o AtCoder, o CodeforcesClient deve falhar nas retentativas e por fim retornar uma lista vazia, evitando crash da app.
    """
    client = CodeforcesClient(timeout=1, sleep_time=0)
    
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        body=requests.exceptions.Timeout("Read timeout"),
    )
    
    data = client.get_user_submissions('toro')
    assert data == []
