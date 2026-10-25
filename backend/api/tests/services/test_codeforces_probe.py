"""Offline coverage for the opt-in, standalone Render access probe."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests


@pytest.fixture
def probe():
    path = Path(__file__).resolve().parents[3] / 'scripts' / 'probe_codeforces.py'
    spec = importlib.util.spec_from_file_location('cf_probe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def response(status=200, body=b'', headers=None):
    value = Mock(status_code=status, headers=headers or {})
    value.iter_content.return_value = [body]
    return value


def test_probe_identifies_challenge_even_with_http_200_without_exposing_content(probe):
    get = Mock(return_value=response(200, b'PRIVATE', {
        'cf-mitigated': 'challenge', 'CF-Ray': 'a4d44bca9e2a302c-PDX',
        'Set-Cookie': 'PRIVATE', 'Server': 'cloudflare'}))
    result = probe.inspect_target(probe.TARGETS[0], get, 'local', 'plain')
    assert result['outcome'] == 'cloudflare_challenge'
    assert result['source_cf_ray'] == 'a4d44bca9e2a302c-PDX'
    assert 'PRIVATE' not in str(result)
    assert get.call_count == 1
    assert get.call_args.kwargs['allow_redirects'] is False


def test_probe_never_confuses_first_problem_with_expected_index(probe):
    html = b'<div class="problem-statement"><div class="header"><div class="title">A. Synthetic</div></div></div>'
    result = probe.inspect_target(probe.TARGETS[1], Mock(return_value=response(body=html)), 'local', 'plain')
    assert result['outcome'] == 'expected_problem_missing'
    assert result['matching_statements'] == 0


@pytest.mark.parametrize('kind,outcome', [
    ('timeout', 'timeout'), ('connection', 'connection_error'),
    ('redirect', 'redirect'), ('large', 'response_too_large'),
])
def test_probe_is_bounded_and_has_no_retry_or_sensitive_error_text(probe, kind, outcome):
    get = Mock()
    if kind in ('timeout', 'connection'):
        get.side_effect = (requests.Timeout if kind == 'timeout' else requests.ConnectionError)('PRIVATE')
    else:
        get.return_value = response(302 if kind == 'redirect' else 200,
                                    b'x' * (probe.MAX_BYTES + 1), {'Location': 'https://PRIVATE'})
    result = probe.inspect_target(probe.TARGETS[0], get, 'render', 'plain')
    assert result['outcome'] == outcome
    assert 'PRIVATE' not in str(result)
    assert get.call_count == 1


def test_probe_budget_can_skip_remaining_targets_and_sleep_is_explicit(probe):
    get, emit, sleep = Mock(), Mock(), Mock()
    probe.run_probe('local', 'plain', get=get, emit=emit, sleep=sleep, clock=Mock(side_effect=[0, 50]))
    get.assert_not_called()
    assert emit.call_args.args[0]['outcome'] == 'time_budget_reached'


def test_probe_selects_correct_statement_and_uses_existing_parser(probe, monkeypatch):
    html = b'''<div class="problem-statement"><div class="header"><div class="title">A. Other</div></div></div>
    <div class="problem-statement"><div class="header"><div class="title">D. Synthetic</div></div></div>'''
    parser = Mock(return_value={'testcases': [{}], 'images': []})
    monkeypatch.setattr(probe.CodeforcesScraper, 'parse_html', parser)
    result = probe.inspect_target(probe.TARGETS[1], Mock(return_value=response(body=html)), 'local', 'plain')
    assert result['outcome'] == 'statement_valid'
    assert result['statement_count'] == 2
    assert result['sample_pairs'] == 1
    assert 'D. Synthetic' in parser.call_args.args[0]
    assert 'A. Other' not in parser.call_args.args[0]


def test_probe_runs_fixed_targets_once_and_closes_all_responses(probe):
    value = response(403, b'PRIVATE')
    get, sleep, emit = Mock(return_value=value), Mock(), Mock()
    probe.run_probe('local', 'plain', get=get, sleep=sleep, emit=emit, clock=lambda: 0)
    assert get.call_count == len(probe.TARGETS) == 5
    assert sleep.call_args_list == [((3,),)] * 4
    assert value.close.call_count == 5
    assert all(call.args[0].startswith('https://codeforces.com/') for call in get.call_args_list)


def test_probe_rejects_duplicate_identity_and_invalid_statement(probe):
    html = b'<div class="problem-statement"><div class="header"><div class="title">D. Synthetic</div></div></div>'
    invalid = probe.inspect_target(probe.TARGETS[1], Mock(return_value=response(body=html)), 'local', 'plain')
    ambiguous = probe.inspect_target(probe.TARGETS[1], Mock(return_value=response(body=html * 2)), 'local', 'plain')
    assert invalid['outcome'] == 'statement_invalid'
    assert ambiguous['outcome'] == 'expected_problem_ambiguous'


def test_unknown_error_does_not_reveal_exception_text(probe):
    result = probe.inspect_target(probe.TARGETS[0], Mock(side_effect=RuntimeError('PRIVATE')), 'local', 'plain')
    assert result['outcome'] == 'unexpected_error'
    assert result['error_type'] == 'RuntimeError'
    assert 'PRIVATE' not in str(result)


def test_session_profile_is_explicit_and_closed(probe, monkeypatch):
    client = Mock()
    session = Mock()
    session.__enter__ = Mock(return_value=client)
    session.__exit__ = Mock()
    monkeypatch.setattr(probe.requests, 'Session', Mock(return_value=session))
    run = Mock()
    monkeypatch.setattr(probe, 'run_probe', run)
    monkeypatch.setattr(probe, 'emit_json', Mock())
    probe.main(['--environment', 'render', '--profile', 'session'])
    assert run.call_args.kwargs['get'] == client.get
    session.__exit__.assert_called_once()
    assert 'ForjaDiagnostics' in client.headers.update.call_args.args[0]['User-Agent']

@pytest.mark.parametrize('kind,outcome', [('timeout', 'timeout'), ('connection', 'connection_error')])
def test_curl_errors_are_classified_without_provider_or_error_text(probe, kind, outcome):
    from curl_cffi.requests import exceptions
    # Native networking is replaced before the C library boundary.
    error = exceptions.Timeout if kind == 'timeout' else exceptions.RequestException
    get = Mock(side_effect=error('PRIVATE'))
    result = probe.inspect_target(probe.TARGETS[0], get, 'render', 'curl_chrome',
                                  network_errors=(exceptions.Timeout, exceptions.RequestException))
    assert result['outcome'] == outcome
    assert 'PRIVATE' not in str(result)
    get.assert_called_once()


def test_curl_profile_only_checks_two_public_individual_pages(probe):
    get, emit, sleep = Mock(return_value=response(403)), Mock(), Mock()
    probe.run_probe('render', 'curl_chrome', get=get, emit=emit, sleep=sleep, clock=lambda: 0)
    assert [call.args[0] for call in get.call_args_list] == [
        'https://codeforces.com/contest/1542/problem/D',
        'https://codeforces.com/gym/106682/problem/H',
    ]
    sleep.assert_called_once_with(3)


def test_curl_profile_uses_fixed_fingerprint_without_proxy_cookies_or_fallback(probe, monkeypatch):
    from curl_cffi import requests as curl_requests
    client = Mock()
    context = Mock(__enter__=Mock(return_value=client), __exit__=Mock())
    factory = Mock(return_value=context)
    monkeypatch.setattr(curl_requests, 'Session', factory)
    run, emit = Mock(), Mock()
    monkeypatch.setattr(probe, 'run_probe', run)
    monkeypatch.setattr(probe, 'emit_json', emit)
    monkeypatch.setattr(probe.requests, 'get', Mock(side_effect=AssertionError('No fallback')))
    probe.main(['--environment', 'render', '--profile', 'curl_chrome'])
    factory.assert_called_once_with(impersonate='chrome150', trust_env=False,
                                     verify=True, discard_cookies=True)
    assert run.call_args.kwargs['get'] == client.get
    start = emit.call_args_list[0].args[0]
    assert start['max_requests'] == 2
    assert start['impersonate'] == 'chrome150'
    assert start['curl_cffi'] == '0.16.3'
    context.__exit__.assert_called_once()


def test_curl_stream_error_is_classified_and_response_closed(probe):
    from curl_cffi.requests import exceptions
    value = response()
    value.iter_content.side_effect = exceptions.Timeout('PRIVATE')
    result = probe.inspect_target(probe.TARGETS[0], Mock(return_value=value), 'render', 'curl_chrome',
                                  network_errors=(exceptions.Timeout, exceptions.RequestException))
    assert result['outcome'] == 'timeout'
    assert 'PRIVATE' not in str(result)
    value.close.assert_called_once()
