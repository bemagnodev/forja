"""Opt-in access diagnosis. No Django setup, database, dotenv or AI imports.

Run from backend: python scripts/probe_codeforces.py --environment local
Output is JSON Lines containing metadata only; no pages are saved.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import ssl
import sys
import time

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.services.scrapers.codeforces import CodeforcesScraper


TARGETS = (
    ('official_individual', '/contest/1542/problem/D', 'D'),
    ('official_contest', '/contest/1542/problems', 'D'),
    ('gym_individual', '/gym/106682/problem/H', 'H'),
    ('gym_contest', '/gym/106682/problems', 'H'),
    ('official_problemset', '/problemset/problem/1542/D', 'D'),
)
MAX_BYTES = 1024 * 1024
BATCH_SECONDS = 45
CURL_VERSION = '0.16.3'
CURL_TARGET = 'chrome150'


def inspect_target(target, get, environment, profile, *, network_errors=None):
    case, path, index = target
    started = time.monotonic()
    result = {'event': 'target', 'environment': environment, 'profile': profile,
              'case': case, 'path': path, 'expected_index': index,
              'at': datetime.now(timezone.utc).isoformat()}
    response = None
    timeout_error, connection_error = network_errors or (requests.Timeout, requests.RequestException)
    try:
        # Do not follow redirects: each target makes exactly one HTTP request.
        response = get('https://codeforces.com' + path, timeout=10,
                       stream=True, allow_redirects=False)
        result['http_status'] = response.status_code
        headers = response.headers
        if headers.get('Server', '').lower() == 'cloudflare':
            result['source_server'] = 'cloudflare'
        ray = headers.get('CF-Ray', '')
        if re.fullmatch(r'[a-fA-F0-9]{16,32}-[A-Z0-9]{3,8}', ray):
            result['source_cf_ray'] = ray
        if headers.get('cf-mitigated') == 'challenge':
            result['outcome'] = 'cloudflare_challenge'
        elif 300 <= response.status_code < 400:
            result['outcome'] = 'redirect'
        elif response.status_code != 200:
            result['outcome'] = 'http_error'
        else:
            body = bytearray()
            chunks = response.iter_content() if profile == 'curl_chrome' else response.iter_content(65536)
            for chunk in chunks:
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    result['outcome'] = 'response_too_large'
                    break
                if time.monotonic() - started >= 15:
                    result['outcome'] = 'response_time_budget_reached'
                    break
            if 'outcome' not in result:
                result['bytes_read'] = len(body)
                roots = BeautifulSoup(bytes(body), 'html.parser').select('div.problem-statement')
                result['statement_count'] = len(roots)
                matches = []
                for root in roots:
                    title = root.select_one('.header .title')
                    if title and re.match(r'^' + re.escape(index) + r'\s*\.', title.get_text(strip=True)):
                        matches.append(root)
                result['matching_statements'] = len(matches)
                if len(matches) != 1:
                    result['outcome'] = 'expected_problem_missing' if not matches else 'expected_problem_ambiguous'
                else:
                    try:
                        parsed = CodeforcesScraper.parse_html(str(matches[0]), 'https://codeforces.com' + path)
                        result.update(outcome='statement_valid', sample_pairs=len(parsed['testcases']),
                                      image_count=len(parsed.get('images', [])))
                    except ValueError:
                        result['outcome'] = 'statement_invalid'
    except timeout_error:
        result['outcome'] = 'timeout'
    except connection_error:
        result['outcome'] = 'connection_error'
    except Exception as exc:
        result.update(outcome='unexpected_error', error_type=type(exc).__name__)
    finally:
        if response is not None:
            response.close()
    result['elapsed_ms'] = round((time.monotonic() - started) * 1000)
    return result


def emit_json(value):
    print(json.dumps(value, ensure_ascii=True), flush=True)


def run_probe(environment, profile, *, get, emit=emit_json, sleep=time.sleep, clock=time.monotonic,
              network_errors=None):
    started = clock()
    targets = (TARGETS[0], TARGETS[2]) if profile == 'curl_chrome' else TARGETS
    for position, target in enumerate(targets):
        if clock() - started >= BATCH_SECONDS:
            emit({'event': 'stop', 'outcome': 'time_budget_reached', 'remaining': len(targets) - position})
            break
        emit(inspect_target(target, get, environment, profile, network_errors=network_errors))
        if position < len(targets) - 1:
            sleep(3)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', choices=['local', 'render'], required=True)
    parser.add_argument('--profile', choices=['plain', 'session', 'curl_chrome'], default='plain')
    args = parser.parse_args(argv)
    metadata = {'event': 'start', 'environment': args.environment, 'profile': args.profile,
               'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'python': platform.python_version(), 'requests': requests.__version__,
               'openssl': ssl.OPENSSL_VERSION, 'max_requests': len(TARGETS),
               'redirects': False, 'retries': 0, 'max_bytes_per_response': MAX_BYTES}
    if args.profile == 'curl_chrome':
        # Lazy import: no native transport in the active scraper or other profiles.
        try:
            import curl_cffi
            from curl_cffi import requests as curl_requests
            from curl_cffi.requests import exceptions as curl_errors
        except ImportError:
            emit_json({'event': 'stop', 'outcome': 'dependency_unavailable', 'required_curl_cffi': CURL_VERSION})
            return
        if curl_cffi.__version__ != CURL_VERSION:
            emit_json({'event': 'stop', 'outcome': 'dependency_version_mismatch', 'required_curl_cffi': CURL_VERSION})
            return
        metadata.update(max_requests=2, curl_cffi=curl_cffi.__version__, impersonate=CURL_TARGET,
                        transport='curl_cffi', environment_proxies=False, discard_cookies=True)
    emit_json(metadata)
    if args.profile == 'plain':
        run_probe(args.environment, args.profile, get=requests.get)
    elif args.profile == 'session':
        # This is an identified HTTP client, not a browser or authenticated session.
        with requests.Session() as session:
            session.headers.update({'User-Agent': 'ForjaDiagnostics/1.0',
                                    'Accept': 'text/html', 'Accept-Language': 'en'})
            run_probe(args.environment, args.profile, get=session.get)
    else:
        with curl_requests.Session(impersonate=CURL_TARGET, trust_env=False,
                                   verify=True, discard_cookies=True) as session:
            run_probe(args.environment, args.profile, get=session.get,
                      network_errors=(curl_errors.Timeout, curl_errors.RequestException))
    emit_json({'event': 'end', 'environment': args.environment, 'profile': args.profile})


if __name__ == '__main__':
    main()
