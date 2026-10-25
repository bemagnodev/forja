"""Codeforces HTML transport validated by the opt-in Render probe.

Each call has its own session: no user cookies, shared authentication or retry.
The parser remains in codeforces.py and is also used by offline datasets.
"""
from urllib.parse import urlsplit
from time import monotonic

from .exceptions import StatementFetchError, _forbidden_diagnostic

BROWSER_TARGET = 'chrome150'
MAX_BYTES = 1024 * 1024


def fetch_codeforces_statement(url):
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == 'https' and parsed.hostname == 'codeforces.com'
                 and parsed.port in (None, 443) and parsed.username is None
                 and parsed.password is None)
    except ValueError:
        valid = False
    if not valid:
        raise StatementFetchError('source_invalid_url')

    # Imported only when fetching Codeforces; other platforms keep requests.
    from curl_cffi import requests as curl_requests
    from curl_cffi.requests import exceptions as curl_errors

    started = monotonic()
    try:
        with curl_requests.Session(impersonate=BROWSER_TARGET, trust_env=False,
                                   verify=True, discard_cookies=True, retry=0) as session:
            response = session.get(url, timeout=10, allow_redirects=False, stream=True)
            try:
                if response.headers.get('cf-mitigated') == 'challenge':
                    raise StatementFetchError('source_challenge', response.status_code,
                                              _forbidden_diagnostic(response, include_challenge=True))
                if response.status_code != 200:
                    raise StatementFetchError('source_http_error', response.status_code,
                                              _forbidden_diagnostic(response))
                body = bytearray()
                for chunk in response.iter_content():
                    if len(body) + len(chunk) > MAX_BYTES:
                        raise StatementFetchError('source_response_too_large')
                    if monotonic() - started >= 15:
                        raise StatementFetchError('source_timeout')
                    body.extend(chunk)
                return body.decode(response.encoding or 'utf-8', errors='replace')
            finally:
                response.close()
    except curl_errors.Timeout:
        raise StatementFetchError('source_timeout') from None
    except curl_errors.RequestException:
        raise StatementFetchError('source_connection_error') from None
