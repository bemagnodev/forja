import pytest
from api.models import User, Contest, Problem


@pytest.fixture(autouse=True)
def prohibit_external_network(monkeypatch):
    """Mocks must terminate HTTP before DNS/socket I/O; even caught attempts fail."""
    import socket
    from curl_cffi import Curl, AsyncCurl
    attempts = []

    def blocked(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("External network is prohibited in backend tests")

    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    # libcurl performs native I/O, bypassing Python's socket monkeypatches.
    monkeypatch.setattr(Curl, "perform", blocked)
    monkeypatch.setattr(AsyncCurl, "add_handle", blocked)
    yield
    assert not attempts, "A test attempted real network I/O despite its mocks"

@pytest.fixture
def base_user():
    return User.objects.create(username="mentor", cf_handle="mentor", atcoder_handle="mentor_ac")

@pytest.fixture
def api_client(client, base_user):
    from ninja_jwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(base_user)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {refresh.access_token}'
    return client

@pytest.fixture
def sample_problem():
    contest = Contest.objects.create(platform='CF_OFFICIAL', platform_id='1000', name='Test Contest')
    return Problem.objects.create(platform='CF_OFFICIAL', platform_id='1000A', title='Math', contest=contest)
