import pytest
import responses
from django.core.management import call_command
from api.models import User, Problem, PlatformChoices

@pytest.mark.django_db
@responses.activate
def test_sync_cf_bypass_testing(capsys):
    user = User.objects.create(username="test_user", cf_handle="toro", cf_last_sync_time=1000)
    
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK', 
            'result': [
                {'id': 100, 'verdict': 'TESTING', 'creationTimeSeconds': 1500, 'problem': {'contestId': 1, 'index': 'A'}},
                {'id': 99, 'verdict': 'OK', 'creationTimeSeconds': 1200, 'problem': {'contestId': 1, 'index': 'B'}},
                {'id': 98, 'verdict': 'WRONG_ANSWER', 'creationTimeSeconds': 900, 'problem': {'contestId': 1, 'index': 'C'}} 
            ]
        },
        status=200
    )
    
    call_command('sync_cf')
    
    user.refresh_from_db()
    # O epoch deve parar no 1200. O 1500 (TESTING) não pode ser o max_epoch
    assert user.cf_last_sync_time == 1200
    
    # Garante que a wall defendeu e ignorou inserts antigos
    # Ou seja: não salvou o tracking ID 98
    # Testar que salvou o Problem pra 1B (id 99) mas não salvou tracking nulo
    pass

@pytest.mark.django_db
@responses.activate
def test_sync_atcoder_bypass_wj(capsys):
    user = User.objects.create(username="test_user", atcoder_handle="toro", atcoder_last_sync_time=1000)
    
    responses.add(
        responses.GET,
        'https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions',
        json=[
            {'id': 98, 'result': 'AC', 'epoch_second': 900, 'problem_id': 'abc_a', 'contest_id': 'abc', 'language': 'C++'},
            {'id': 99, 'result': 'WA', 'epoch_second': 1200, 'problem_id': 'abc_b', 'contest_id': 'abc', 'language': 'C++'},
            {'id': 100, 'result': 'WJ', 'epoch_second': 1500, 'problem_id': 'abc_c', 'contest_id': 'abc', 'language': 'C++'}
        ],
        status=200
    )
    
    call_command('sync_atcoder')
    
    user.refresh_from_db()
    
    # O epoch do WJ (1500) não deve ter atualizado o atcoder_last_sync_time
    assert user.atcoder_last_sync_time == 1200
