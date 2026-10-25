class UnparseableProblemException(Exception):
    pass


class StatementFetchError(Exception):
    def __init__(self, code, http_status=None, source_diagnostic=None):
        super().__init__(code)
        self.code = code
        self.http_status = http_status if type(http_status) is int else None
        self.source_diagnostic = source_diagnostic or {}


def _forbidden_diagnostic(response, *, include_challenge=False):
    """Classify evidence, never return page text, cookies or arbitrary headers."""
    import re
    if response is None:
        return {}
    headers = response.headers
    if not hasattr(headers, 'get'):
        return {}
    if response.status_code != 403 and not (include_challenge and headers.get('cf-mitigated') == 'challenge'):
        return {}
    result = {'source_category': 'unknown'}
    server = headers.get('Server', '')
    if isinstance(server, str) and server.lower() == 'cloudflare':
        result['source_server'] = 'cloudflare'
    ray = headers.get('CF-Ray', '')
    if isinstance(ray, str) and re.fullmatch(r'[a-fA-F0-9]{16,32}-[A-Z0-9]{3,8}', ray):
        result['source_cf_ray'] = ray
    if headers.get('cf-mitigated') == 'challenge':
        result['source_category'] = 'cloudflare_challenge'
    else:
        content = response.content
        if isinstance(content, bytes) and b'attention required! | cloudflare' in content[:32768].lower():
            result['source_category'] = 'cloudflare_block'
    return result


def fetch_statement(url, get):
    """One fetch; preserve safe diagnostics without URLs or response bodies."""
    import requests
    try:
        response = get(url, timeout=10)
        response.raise_for_status()
        return response
    except requests.Timeout:
        raise StatementFetchError('source_timeout') from None
    except requests.HTTPError as exc:
        raise StatementFetchError('source_http_error', getattr(exc.response, 'status_code', None),
                                  _forbidden_diagnostic(exc.response)) from None
    except requests.RequestException:
        raise StatementFetchError('source_connection_error') from None
