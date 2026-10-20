from unittest.mock import Mock

import pytest
import requests


@pytest.mark.parametrize('platform', ['cses', 'atcoder'])
def test_live_scrapers_extract_paired_samples_from_current_structure(platform, monkeypatch):
    from api.services.scrapers import CSESScraper, AtCoderScraper
    if platform == 'cses':
        html = '''<div class="content"><ul class="task-constraints"></ul><div class="md">
        <p>Synthetic statement.</p><h1 id="input">Input</h1><p>Two integers.</p>
        <h1 id="output">Output</h1><p>The sum.</p><h1 id="example">Example</h1>
        <b>Input:</b><pre>1 2\n3 4</pre><b>Output:</b><pre>3\n7</pre></div></div>'''
        scraper = CSESScraper()
    else:
        html = '''<div id="task-statement"><span class="lang-en">
        <section><h3>Problem Statement</h3><p>Synthetic statement.</p></section>
        <section><h3>Input</h3><pre>Two integers.</pre></section>
        <section><h3>Output</h3><p>The sum.</p></section>
        <section><h3>Sample Input 1</h3><pre>1 2\n3 4</pre></section>
        <section><h3>Sample Output 1</h3><pre>3\n7</pre></section>
        <section><h3>Sample Input 2</h3><pre>5 6</pre></section>
        <section><h3>Sample Output 2</h3><pre>11</pre></section></span></div>'''
        scraper = AtCoderScraper()
    html = html.replace('1 2\n3 4', '1 2<br>3 4')
    monkeypatch.setattr(requests, 'get', Mock(return_value=Mock(content=html.encode())))
    result = scraper.scrape('https://example.invalid/task')
    assert result['description'] == 'Synthetic statement.'
    assert result['input_format'] == 'Two integers.'
    assert result['testcases'][0] == {'input': '1 2\n3 4', 'output': '3\n7'}
    assert len(result['testcases']) == (1 if platform == 'cses' else 2)


@pytest.mark.parametrize('platform', ['cses', 'atcoder'])
def test_scrapers_reject_unpaired_samples_instead_of_silently_losing_them(platform, monkeypatch):
    from api.services.scrapers import CSESScraper, AtCoderScraper
    from api.services.scrapers.exceptions import UnparseableProblemException
    html = ('<div class="content"><div class="md"><p>Statement</p><h1 id="example">Example</h1><pre>1</pre></div></div>'
            if platform == 'cses' else '<div id="task-statement"><section><h3>Sample Input 1</h3><pre>1</pre></section></div>')
    monkeypatch.setattr(requests, 'get', Mock(return_value=Mock(content=html.encode())))
    with pytest.raises(UnparseableProblemException):
        (CSESScraper() if platform == 'cses' else AtCoderScraper()).scrape('https://example.invalid/task')


@pytest.mark.django_db
@pytest.mark.parametrize('platform', ['CF_OFFICIAL', 'ATCODER', 'CSES'])
@pytest.mark.parametrize('route', ['problems/{id}/predict', 'ai-lab/problems/{id}/classify'])
@pytest.mark.parametrize('failure,code,upstream', [('blocked', 'source_http_error', 403), ('timeout', 'source_timeout', None)])
def test_fetch_failure_is_safe_identifiable_and_never_calls_ai(platform, route, failure, code, upstream,
        api_client, sample_problem, monkeypatch):
    from api import api as routes
    sample_problem.platform = platform
    sample_problem.save()
    error = requests.Timeout('SECRET') if failure == 'timeout' else requests.HTTPError('SECRET', response=Mock(status_code=403))
    monkeypatch.setattr(requests, 'get', Mock(side_effect=error))
    classify = Mock()
    monkeypatch.setattr(routes, 'classify_problem', classify)
    response = api_client.post('/api/' + route.format(id=sample_problem.pk))
    assert response.status_code in (502, 504)
    body = response.json()
    assert body['diagnostic']['stage'] == 'fetch'
    assert body['diagnostic']['code'] == code
    assert body['diagnostic']['upstream_status'] == upstream
    assert body['diagnostic']['request_id']
    assert 'SECRET' not in response.content.decode()
    classify.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize('category,http,code,stage', [
    ('authentication', None, 'provider_not_configured', 'provider'),
    ('authentication', 403, 'provider_access_denied', 'provider'),
    ('parsing', 200, 'parsing', 'provider'),
    ('rate_limit', 429, 'rate_limit', 'provider'),
])
def test_provider_diagnostic_distinguishes_configuration_from_remote_failure(category, http, code, stage,
        api_client, sample_problem, explore_statement, monkeypatch, caplog):
    from api import api as routes
    from api.ai_lab.contracts import ProviderFailure
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr('api.services.scrapers.CodeforcesScraper', lambda: scraper)
    monkeypatch.setattr(routes, 'classify_problem', Mock(side_effect=ProviderFailure(category, http_status=http)))
    response = api_client.post(f'/api/ai-lab/problems/{sample_problem.pk}/classify')
    diagnostic = response.json()['diagnostic']
    assert (diagnostic['code'], diagnostic['stage'], diagnostic['upstream_status']) == (code, stage, http)
    assert diagnostic['request_id'] in caplog.text
    sample_problem.refresh_from_db()
    assert 'ai_rating' not in sample_problem.platform_metadata


@pytest.mark.django_db
def test_missing_input_is_reported_before_generation(api_client, sample_problem, monkeypatch):
    from api.ai_lab import explore
    scraper = Mock()
    scraper.scrape.return_value = {'description': 'Synthetic', 'input_format': '', 'output_format': 'One integer'}
    monkeypatch.setattr('api.services.scrapers.CodeforcesScraper', lambda: scraper)
    generator = Mock()
    monkeypatch.setattr(explore, 'get_generator', generator)
    response = api_client.post(f'/api/ai-lab/problems/{sample_problem.pk}/classify')
    assert response.status_code == 400
    assert response.json()['diagnostic']['stage'] == 'prepare'
    assert 'input_format' in response.json()['detail']
    generator.assert_not_called()


@pytest.mark.django_db
def test_unexpected_classification_error_never_exposes_exception_message(api_client, sample_problem,
        explore_statement, monkeypatch, caplog):
    from api import api as routes
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr('api.services.scrapers.CodeforcesScraper', lambda: scraper)
    monkeypatch.setattr(routes, 'classify_problem', Mock(side_effect=RuntimeError('SECRET')))
    response = api_client.post(f'/api/ai-lab/problems/{sample_problem.pk}/classify')
    assert response.status_code == 503
    assert response.json()['diagnostic']['code'] == 'unexpected_error'
    assert 'SECRET' not in response.content.decode() + caplog.text


@pytest.mark.django_db
@pytest.mark.parametrize('route', ['problems/{id}/predict', 'ai-lab/problems/{id}/classify'])
def test_unexpected_scraper_failure_has_safe_diagnostic_and_never_calls_ai(route,
        api_client, sample_problem, monkeypatch, caplog):
    from api import api as routes
    scraper = Mock()
    scraper.scrape.side_effect = RuntimeError('SECRET')
    monkeypatch.setattr('api.services.scrapers.CodeforcesScraper', lambda: scraper)
    classify = Mock()
    monkeypatch.setattr(routes, 'classify_problem', classify)
    response = api_client.post('/api/' + route.format(id=sample_problem.pk))
    assert response.status_code == 503
    assert response.json()['diagnostic']['stage'] == 'extract'
    assert response.json()['diagnostic']['code'] == 'unexpected_error'
    assert 'SECRET' not in response.content.decode() + caplog.text
    classify.assert_not_called()

@pytest.mark.parametrize('route', ['problems/{id}/predict', 'ai-lab/problems/{id}/classify'])
@pytest.mark.django_db
def test_403_metadata_is_safe_and_visible_in_response_and_logs(route, api_client, sample_problem, monkeypatch, caplog):
    from api import api as routes
    response = requests.Response()
    response.status_code = 403
    response.headers.update({'Server': 'cloudflare', 'CF-Ray': 'a4d111ae5e63e0e3-GIG',
                             'cf-mitigated': 'challenge', 'Set-Cookie': 'PRIVATE'})
    response._content = b'<title>PRIVATE</title>'
    monkeypatch.setattr(requests, 'get', Mock(return_value=response))
    classify = Mock()
    monkeypatch.setattr(routes, 'classify_problem', classify)
    result = api_client.post('/api/' + route.format(id=sample_problem.pk))
    diagnostic = result.json()['diagnostic']
    assert diagnostic['source_category'] == 'cloudflare_challenge'
    assert diagnostic['source_server'] == 'cloudflare'
    assert diagnostic['source_cf_ray'] == 'a4d111ae5e63e0e3-GIG'
    assert diagnostic['source_cf_ray'] in caplog.text
    assert 'PRIVATE' not in result.content.decode() + caplog.text
    classify.assert_not_called()


@pytest.mark.parametrize('headers,body,category', [
    ({'Server': 'cloudflare'}, b'Forbidden', 'unknown'),
    ({'Server': 'cloudflare'}, b'<title>Attention Required! | Cloudflare</title>', 'cloudflare_block'),
    ({'Server': 'PRIVATE\r\nInjected', 'CF-Ray': 'PRIVATE'}, b'PRIVATE', 'unknown'),
])
def test_403_does_not_invent_challenge_or_expose_arbitrary_headers(headers, body, category):
    from api.services.scrapers.exceptions import fetch_statement, StatementFetchError
    response = requests.Response()
    response.status_code = 403
    response.headers.update(headers)
    response._content = body
    with pytest.raises(StatementFetchError) as caught:
        fetch_statement('https://example.invalid', Mock(return_value=response))
    assert caught.value.source_diagnostic['source_category'] == category
    assert 'PRIVATE' not in str(caught.value.source_diagnostic)

@pytest.mark.parametrize('status', [200, 429, 500])
def test_fetch_metadata_is_limited_to_403_and_does_not_retry(status):
    from api.services.scrapers.exceptions import fetch_statement, StatementFetchError
    response = requests.Response()
    response.status_code = status
    response.headers['cf-mitigated'] = 'challenge'
    response._content = b'PRIVATE'
    get = Mock(return_value=response)
    if status == 200:
        assert fetch_statement('https://example.invalid', get) is response
    else:
        with pytest.raises(StatementFetchError) as caught:
            fetch_statement('https://example.invalid', get)
        assert caught.value.source_diagnostic == {}
    get.assert_called_once_with('https://example.invalid', timeout=10)
