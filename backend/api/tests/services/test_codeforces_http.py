"""Codeforces-only HTTP transport and real route orchestration, with no network."""
from unittest.mock import Mock

import pytest
import requests
from curl_cffi import requests as curl_requests
from curl_cffi.requests import exceptions as curl_errors

from api.services.scrapers.codeforces import CodeforcesScraper
from api.services.scrapers.exceptions import StatementFetchError
from api.tests.services.test_scrapers import SAMPLE_HTML


@pytest.fixture
def native_client(monkeypatch):
    response = requests.Response()
    response.status_code = 200
    response._content = SAMPLE_HTML.encode()
    response._content_consumed = True
    response.encoding = 'utf-8'
    client = Mock()
    client.get.return_value = response
    context = Mock(__enter__=Mock(return_value=client), __exit__=Mock(return_value=False))
    factory = Mock(return_value=context)
    monkeypatch.setattr(curl_requests, 'Session', factory)
    monkeypatch.setattr(requests, 'get', Mock(side_effect=AssertionError('No requests fallback')))
    return client, response, factory, context


def test_codeforces_uses_browser_transport_once_without_changing_parser(native_client):
    client, _, factory, context = native_client
    result = CodeforcesScraper().scrape('https://codeforces.com/contest/1/problem/A')
    assert result == CodeforcesScraper.parse_html(SAMPLE_HTML, 'https://codeforces.com/contest/1/problem/A')
    factory.assert_called_once_with(impersonate='chrome150', trust_env=False,
                                     verify=True, discard_cookies=True, retry=0)
    client.get.assert_called_once_with('https://codeforces.com/contest/1/problem/A',
                                      timeout=10, allow_redirects=False, stream=True)
    context.__exit__.assert_called_once()


@pytest.mark.parametrize('error,code', [(curl_errors.Timeout, 'source_timeout'),
                                      (curl_errors.ConnectionError, 'source_connection_error')])
def test_native_errors_are_safe_and_not_retried(native_client, error, code):
    client, _, _, context = native_client
    client.get.side_effect = error('PRIVATE')
    with pytest.raises(StatementFetchError) as caught:
        CodeforcesScraper().scrape('https://codeforces.com/gym/106682/problem/H')
    assert caught.value.code == code
    assert 'PRIVATE' not in str(caught.value)
    assert client.get.call_count == 1
    context.__exit__.assert_called_once()


def test_native_response_is_bounded_and_closed(native_client, monkeypatch):
    _, response, _, _ = native_client
    response._content = b'x' * (1024 * 1024 + 1)
    close = Mock(wraps=response.close)
    monkeypatch.setattr(response, 'close', close)
    with pytest.raises(StatementFetchError) as caught:
        CodeforcesScraper().scrape('https://codeforces.com/contest/1/problem/A')
    assert caught.value.code == 'source_response_too_large'
    close.assert_called_once()


def test_native_stream_timeout_is_safe_and_closed(native_client, monkeypatch):
    _, response, _, _ = native_client
    monkeypatch.setattr(response, 'iter_content', Mock(side_effect=curl_errors.Timeout('PRIVATE')))
    close = Mock(wraps=response.close)
    monkeypatch.setattr(response, 'close', close)
    with pytest.raises(StatementFetchError) as caught:
        CodeforcesScraper().scrape('https://codeforces.com/contest/1/problem/A')
    assert caught.value.code == 'source_timeout'
    assert 'PRIVATE' not in str(caught.value)
    close.assert_called_once()


def test_slow_stream_is_interrupted_without_classifying_partial_text(native_client, monkeypatch):
    from api.services.scrapers import codeforces_http
    _, response, _, _ = native_client
    monkeypatch.setattr(codeforces_http, 'monotonic', Mock(side_effect=[0, 16]))
    parser = Mock()
    monkeypatch.setattr(CodeforcesScraper, 'parse_html', parser)
    with pytest.raises(StatementFetchError) as caught:
        CodeforcesScraper().scrape('https://codeforces.com/contest/1/problem/A')
    assert caught.value.code == 'source_timeout'
    parser.assert_not_called()


@pytest.mark.parametrize('status,challenge,code', [
    (403, True, 'source_challenge'), (200, True, 'source_challenge'),
    (403, False, 'source_http_error'), (302, False, 'source_http_error'),
    (429, False, 'source_http_error'), (500, False, 'source_http_error'),
])
def test_http_failures_never_reach_parser_or_expose_content(native_client, status, challenge, code, monkeypatch):
    client, response, _, context = native_client
    response.status_code = status
    response._content = b'PRIVATE'
    response.headers.update({'Server': 'cloudflare', 'CF-Ray': 'a504173508c0147f-PDX',
                             'Set-Cookie': 'PRIVATE', 'Location': 'https://PRIVATE'})
    if challenge:
        response.headers['cf-mitigated'] = 'challenge'
    parser = Mock()
    monkeypatch.setattr(CodeforcesScraper, 'parse_html', parser)
    with pytest.raises(StatementFetchError) as caught:
        CodeforcesScraper().scrape('https://codeforces.com/contest/1/problem/A')
    assert caught.value.code == code
    assert caught.value.http_status == status
    assert 'PRIVATE' not in str(caught.value.source_diagnostic)
    if challenge:
        assert caught.value.source_diagnostic['source_category'] == 'cloudflare_challenge'
    assert client.get.call_count == 1
    parser.assert_not_called()
    context.__exit__.assert_called_once()


@pytest.mark.parametrize('url', ['http://codeforces.com/contest/1/problem/A',
    'https://example.invalid/', 'https://codeforces.com.example.invalid/',
    'https://user:PRIVATE@codeforces.com/contest/1/problem/A'])
def test_native_transport_rejects_non_codeforces_or_credential_urls_before_network(native_client, url):
    _, _, factory, _ = native_client
    with pytest.raises(StatementFetchError) as caught:
        CodeforcesScraper().scrape(url)
    assert caught.value.code == 'source_invalid_url'
    factory.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize('platform', ['CF_OFFICIAL', 'CF_GYM'])
@pytest.mark.parametrize('route', ['problems/{id}/predict', 'ai-lab/problems/{id}/classify'])
def test_explore_queue_and_contests_use_new_transport_with_simulated_ai(native_client, api_client,
        sample_problem, platform, route, monkeypatch):
    from api import api as routes
    sample_problem.platform = platform
    sample_problem.save()
    generate = Mock(return_value={'predicted_rating': 1200, 'predicted_tags': ['math'],
                                 'reasoning': 'Synthetic'})
    monkeypatch.setattr(routes, 'classify_problem', generate)
    response = api_client.post('/api/' + route.format(id=sample_problem.pk))
    assert response.status_code == 200
    client = native_client[0]
    client.get.assert_called_once()
    generate.assert_called_once()
    assert generate.call_args.args[0]['testcases'] == [{'input': '1', 'output': '2'}]
    sample_problem.refresh_from_db()
    if route.startswith('ai-lab'):
        assert 'ai_rating' not in sample_problem.platform_metadata
    else:
        assert sample_problem.platform_metadata['ai_rating'] == 1200
        assert api_client.post('/api/' + route.format(id=sample_problem.pk)).json()['cached'] is True
        client.get.assert_called_once()
        generate.assert_called_once()


@pytest.mark.django_db
@pytest.mark.parametrize('status', [200, 403])
@pytest.mark.parametrize('route', ['problems/{id}/predict', 'ai-lab/problems/{id}/classify'])
def test_challenge_at_any_status_stops_before_ai_with_diagnostic(native_client, api_client,
        sample_problem, status, route, monkeypatch, caplog):
    from api import api as routes
    _, value, _, _ = native_client
    value.status_code = status
    value._content = b'PRIVATE'
    value.headers.update({'cf-mitigated': 'challenge', 'Server': 'cloudflare',
                          'CF-Ray': 'a504173508c0147f-PDX'})
    generate = Mock()
    monkeypatch.setattr(routes, 'classify_problem', generate)
    response = api_client.post('/api/' + route.format(id=sample_problem.pk))
    assert response.status_code == 502
    assert response.json()['diagnostic']['code'] == 'source_challenge'
    assert response.json()['diagnostic']['upstream_status'] == status
    assert 'verificação' in response.json()['detail']
    assert 'PRIVATE' not in response.content.decode() + caplog.text
    generate.assert_not_called()
