import pytest
from api.models import User, Contest, Problem

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
