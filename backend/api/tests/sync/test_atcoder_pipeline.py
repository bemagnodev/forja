import pytest
import responses
from django.core.management import call_command
from api.models import User, Problem, Submission


@pytest.mark.django_db
@responses.activate
def test_sync_atcoder_bypass_wj(capsys):
    """
    Cenário: O usuário tem três submissões no AtCoder: uma antiga, uma válida nova, e uma 'WJ' (Waiting Judge) mais recente.
    Resultado Esperado:
    1. A submissão 'WJ' é ignorada, e o 'last_sync_time' avança apenas até o epoch da submissão válida mais recente (1200).
    2. A submissão id 99 (nova, válida) salva no banco e gera tracking.
    3. A submissão antiga (id 98) é barrada pela proteção incremental.
    """
    user = User.objects.create(username="test_user", atcoder_handle="toro", atcoder_last_sync_time=1000)
    
    responses.add(
        responses.GET,
        'https://kenkoooo.com/atcoder/resources/problems.json',
        json=[
            {'id': 'abc_a', 'title': 'Task A'},
            {'id': 'abc_b', 'title': 'Task B'},
            {'id': 'abc_c', 'title': 'Task C'}
        ],
        status=200
    )
    
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
    assert user.atcoder_last_sync_time == 1200
    assert Submission.objects.filter(platform_submission_id="99").exists()
    assert not Submission.objects.filter(platform_submission_id="98").exists()


@pytest.mark.django_db
@responses.activate
def test_sync_atcoder_title_mapping():
    """Testa se o título real do problema é mapeado corretamente usando problems.json"""
    user = User.objects.create(username="test_user2", atcoder_handle="tourist", atcoder_last_sync_time=0)
    
    responses.add(
        responses.GET,
        'https://kenkoooo.com/atcoder/resources/problems.json',
        json=[
            {'id': 'dp_a', 'title': 'Frog 1'}
        ],
        status=200
    )
    
    responses.add(
        responses.GET,
        'https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions',
        json=[
            {'id': 1, 'result': 'AC', 'epoch_second': 1000, 'problem_id': 'dp_a', 'contest_id': 'dp', 'language': 'C++'}
        ],
        status=200
    )
    
    call_command('sync_atcoder')
    
    problem = Problem.objects.get(platform_id='dp_a')
    assert problem.title == 'Frog 1'
