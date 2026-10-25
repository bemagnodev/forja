import pytest
import requests
import responses
from api.services.codeforces_client import CodeforcesClient
from api.services.atcoder_client import AtCoderClient
from unittest.mock import patch


@responses.activate
def test_cf_public_history_is_anonymous_with_server_credentials():
    client = CodeforcesClient(sleep_time=0, api_key="private-key", api_secret="private-secret")
    responses.get('https://codeforces.com/api/user.status', json={'status': 'OK', 'result': []})
    result = client.get_user_submissions_result('tourist')
    assert result.is_success and result.data == []
    assert 'apiKey' not in responses.calls[0].request.url


@responses.activate
def test_cf_shared_rate_limit_applies_between_clients_even_after_failure():
    responses.get('https://codeforces.com/api/user.status', status=503)
    with patch('api.services.codeforces_client.time.monotonic', side_effect=[10, 10, 10.5, 12]), \
         patch('api.services.codeforces_client.time.sleep') as sleep:
        CodeforcesClient().get_user_submissions('one')
        CodeforcesClient().get_user_submissions('two')
    sleep.assert_called_once_with(1.5)


@responses.activate
def test_cf_cloudflare_forbidden_is_not_a_permanently_private_gym():
    responses.get('https://codeforces.com/api/contest.standings', status=403,
                  body='<html>Cloudflare challenge</html>')
    result = CodeforcesClient().get_gym_standings_result('106687')
    assert result.is_transient


@responses.activate
def test_cf_gym_catalog_uses_server_signature_but_public_catalog_does_not():
    client = CodeforcesClient(api_key='fake-key', api_secret='fake-secret')
    responses.get('https://codeforces.com/api/contest.standings',
                  json={'status': 'OK', 'result': {'contest': {}, 'problems': []}})
    responses.get('https://codeforces.com/api/contest.list', json={'status': 'OK', 'result': []})
    client.get_gym_standings_result('106687')
    client.get_contests()
    assert 'apiKey=fake-key' in responses.calls[0].request.url
    assert 'apiSig=' in responses.calls[0].request.url
    assert 'apiKey=' not in responses.calls[1].request.url


@responses.activate
@pytest.mark.parametrize('payload', ['not json', '{"status": "OK", "result": {}}'])
def test_cf_malformed_history_is_failure_not_empty(payload):
    responses.get('https://codeforces.com/api/user.status', body=payload)
    assert not CodeforcesClient().get_user_submissions_result('tourist').is_success


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


@responses.activate
def test_codeforces_client_sanitizes_credentials_in_logs_and_errors(capsys):
    """
    Cenário: A chamada ao Codeforces falha e conteria query params sensíveis (apiKey, apiSig).
    Resultado Esperado: As mensagens de log e stdout NÃO podem conter apiKey nem apiSig,
    mas devem preservar o endpoint e informações necessárias para diagnóstico.
    """
    secret_key = "super_secret_api_key_12345"
    secret_sig = "abcdef0123456789abcdef0123456789"
    client = CodeforcesClient(sleep_time=0, api_key=secret_key, api_secret="super_secret_secret")

    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=400,
        body="Contest is not visible"
    )

    result = client.get_gym_standings("106682")
    captured = capsys.readouterr()

    # O segredo e apiSig não devem vazar nem no stdout nem no stderr
    assert secret_key not in captured.out
    assert secret_key not in captured.err
    assert secret_sig not in captured.out
    assert secret_sig not in captured.err
    assert "super_secret_secret" not in captured.out
    assert "super_secret_secret" not in captured.err

    # Diagnóstico útil deve estar presente
    assert "contest.standings" in (captured.out + captured.err)
    assert "400" in (captured.out + captured.err)


@responses.activate
def test_codeforces_client_distinguishes_permanent_and_transient_errors():
    """
    Cenário: Diferenciação entre erros permanentes (400, 403, 404, status FAILED contest não visível)
    e transitórios (500, 502, 503, 429, Timeout).
    Resultado Esperado: get_gym_standings_result retorna um CFResult com flags tipadas.
    """
    client = CodeforcesClient(sleep_time=0)

    # 1. Permanente: HTTP 400
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=400,
        body="Contest is not visible"
    )
    res_perm = client.get_gym_standings_result("106682")
    assert res_perm.is_permanent
    assert not res_perm.is_transient
    assert not res_perm.is_success
    assert res_perm.status_code == 400

    # 2. Transitório: HTTP 500
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=500,
        body="Internal Server Error"
    )
    res_trans = client.get_gym_standings_result("106683")
    assert res_trans.is_transient
    assert not res_trans.is_permanent
    assert not res_trans.is_success
    assert res_trans.status_code == 500

    # 3. Sucesso: HTTP 200 com status OK
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=200,
        json={'status': 'OK', 'result': {'contest': {'name': 'Test Gym'}, 'problems': []}}
    )
    res_ok = client.get_gym_standings_result("106684")
    assert res_ok.is_success
    assert not res_ok.is_permanent
    assert not res_ok.is_transient
    assert res_ok.data['contest']['name'] == 'Test Gym'


@responses.activate
def test_codeforces_client_http_400_detailed_classification(capsys):
    """
    Seção 6: Classificação detalhada de erros HTTP 400 no CodeforcesClient.
    1. Gym 'not visible' ou 'not found' -> permanente.
    2. HTTP 400 com rate limit no comment/body -> transitório.
    3. HTTP 400 com assinatura/API key inválida -> erro de configuração/transitório (não permanente).
    4. HTTP 400 desconhecido -> transitório (não avança watermark nem faz fallback permanente).
    5. Nenhuma mensagem contém valores de apiKey, apiSig ou secret.
    """
    secret_key = "sensitive_key_999"
    secret_sig = "sensitive_sig_888"
    secret_val = "sensitive_secret_777"
    client = CodeforcesClient(sleep_time=0, api_key=secret_key, api_secret=secret_val)

    # 1. Gym not visible -> permanente
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=400,
        json={'status': 'FAILED', 'comment': 'Contest 106682 is not visible to you'}
    )
    res1 = client.get_gym_standings_result("106682")
    assert res1.is_permanent
    assert not res1.is_transient

    # 2. HTTP 400 com rate limit -> transitório
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=400,
        json={'status': 'FAILED', 'comment': 'Call limit exceeded. Try again in 1 second'}
    )
    res2 = client.get_gym_standings_result("106683")
    assert res2.is_transient
    assert not res2.is_permanent

    # 3. HTTP 400 com chave de API / assinatura inválida -> erro de auth (não permanente)
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=400,
        json={'status': 'FAILED', 'comment': f'apiKey={secret_key}: Invalid api key or apiSig={secret_sig}'}
    )
    res3 = client.get_gym_standings_result("106684")
    assert res3.is_transient
    assert not res3.is_permanent

    # 4. HTTP 400 desconhecido -> transitório (não deve virar permanente por omissão)
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=400,
        json={'status': 'FAILED', 'comment': 'Some unexpected internal validation error'}
    )
    res4 = client.get_gym_standings_result("106685")
    assert res4.is_transient
    assert not res4.is_permanent

    # 5. Nenhuma mensagem contém segredos em logs/saída
    captured = capsys.readouterr()
    assert secret_key not in captured.out
    assert secret_key not in captured.err
    assert secret_sig not in captured.out
    assert secret_sig not in captured.err
    assert secret_val not in captured.out
    assert secret_val not in captured.err


@responses.activate
def test_codeforces_client_http_200_failed_status_detailed_classification(capsys):
    """
    Classificação detalhada para respostas com HTTP 200 e 'status': 'FAILED'.
    - 'Contest is not visible' -> PERMANENT
    - 'Contest not found' ou 'Wrong contest id' -> PERMANENT
    - rate limit -> TRANSIENT
    - 'Invalid API key' -> TRANSIENT (não permanente)
    - 'Wrong apiSig' -> TRANSIENT (não permanente)
    - erro desconhecido -> TRANSIENT
    - valores sensíveis continuam ausentes da saída
    """
    secret_key = "sensitive_key_555"
    secret_sig = "sensitive_sig_666"
    secret_val = "sensitive_secret_777"
    client = CodeforcesClient(sleep_time=0, api_key=secret_key, api_secret=secret_val)

    # 1. Contest is not visible -> PERMANENT
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=200,
        json={'status': 'FAILED', 'comment': 'Contest is not visible'}
    )
    res1 = client.get_gym_standings_result("200001")
    assert res1.is_permanent
    assert not res1.is_transient

    # 2. Contest not found / Wrong contest id -> PERMANENT
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=200,
        json={'status': 'FAILED', 'comment': 'Wrong contest id'}
    )
    res2 = client.get_gym_standings_result("200002")
    assert res2.is_permanent
    assert not res2.is_transient

    # 3. Rate limit -> TRANSIENT
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=200,
        json={'status': 'FAILED', 'comment': 'Call limit exceeded'}
    )
    res3 = client.get_gym_standings_result("200003")
    assert res3.is_transient
    assert not res3.is_permanent

    # 4. Invalid API key -> TRANSIENT
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=200,
        json={'status': 'FAILED', 'comment': f'apiKey={secret_key}: Invalid API key'}
    )
    res4 = client.get_gym_standings_result("200004")
    assert res4.is_transient
    assert not res4.is_permanent

    # 5. Wrong apiSig -> TRANSIENT
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=200,
        json={'status': 'FAILED', 'comment': f'apiSig={secret_sig}: Wrong apiSig'}
    )
    res5 = client.get_gym_standings_result("200005")
    assert res5.is_transient
    assert not res5.is_permanent

    # 6. Erro desconhecido -> TRANSIENT
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=200,
        json={'status': 'FAILED', 'comment': 'Something totally unexpected'}
    )
    res6 = client.get_gym_standings_result("200006")
    assert res6.is_transient
    assert not res6.is_permanent

    # 7. Nenhum segredo na saída
    captured = capsys.readouterr()
    assert secret_key not in captured.out
    assert secret_key not in captured.err
    assert secret_sig not in captured.out
    assert secret_sig not in captured.err
    assert secret_val not in captured.out
    assert secret_val not in captured.err
