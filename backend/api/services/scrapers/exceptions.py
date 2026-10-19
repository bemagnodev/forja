class UnparseableProblemException(Exception):
    pass


class StatementFetchError(Exception):
    def __init__(self, code, http_status=None):
        super().__init__(code)
        self.code = code
        self.http_status = http_status if type(http_status) is int else None


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
        raise StatementFetchError('source_http_error', getattr(exc.response, 'status_code', None)) from None
    except requests.RequestException:
        raise StatementFetchError('source_connection_error') from None
