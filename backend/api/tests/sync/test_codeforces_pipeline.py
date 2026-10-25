import pytest
import responses
from django.core.management import call_command
from api.models import User, Problem, Submission, UserProblemTracking, PlatformChoices
from django.core.management.base import CommandError


@pytest.mark.django_db
@responses.activate
@pytest.mark.parametrize("fail_on_second_page", [False, True])
def test_sync_cf_failed_history_preserves_checkpoint_and_can_resume(fail_on_second_page):
    """Uma página com erro não equivale a fim do histórico nem permite avançar o checkpoint."""
    user = User.objects.create(username="paging", cf_handle="paging", cf_last_sync_time=1000)
    submission = {'id': 501, 'verdict': 'OK', 'creationTimeSeconds': 2000,
                  'problem': {'contestId': 1542, 'index': 'D'},
                  'author': {'participantType': 'PRACTICE'}}
    url = 'https://codeforces.com/api/user.status'
    if fail_on_second_page:
        responses.get(url, json={'status': 'OK', 'result': [submission]})
    responses.get(url, json={'status': 'FAILED', 'comment': 'Call limit exceeded'}, status=429)

    with pytest.raises(CommandError, match="histórico"):
        call_command('sync_cf', handle='paging')

    user.refresh_from_db()
    assert user.cf_last_sync_time == 1000
    assert not Submission.objects.filter(user=user).exists()

    responses.reset()
    responses.get(url, json={'status': 'OK', 'result': [submission]})
    responses.get(url, json={'status': 'OK', 'result': []})
    call_command('sync_cf', handle='paging')
    call_command('sync_cf', handle='paging')
    user.refresh_from_db()
    assert user.cf_last_sync_time == 2000
    assert Submission.objects.filter(user=user).count() == 1


@pytest.mark.django_db
@responses.activate
def test_sync_cf_bypass_testing(capsys):
    """
    Cenário: Uma submissão do Codeforces (CF) cai com veredito 'TESTING' (ainda rodando) e existem submissões antigas na frente que estão atrás da "parede" (incremental wall).
    Resultado Esperado: 
    1. O script não pode avançar o 'last_sync_time' com a submissão TESTING (ela precisa ser reavaliada depois).
    2. O script DEVE salvar a submissão válida (id 99).
    3. O script NÃO DEVE salvar a submissão velha (id 98), pois o seu epoch time (900) é menor que o last_sync_time do usuário (1000).
    """
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
    assert user.cf_last_sync_time == 1200
    
    assert Submission.objects.filter(platform_submission_id="99").exists()
    assert UserProblemTracking.objects.filter(problem__platform_id="1B").exists()
    
    assert not Submission.objects.filter(platform_submission_id="98").exists()
    assert not UserProblemTracking.objects.filter(problem__platform_id="1C").exists()


@pytest.mark.django_db
@responses.activate
def test_sync_cf_contest_participation_shield():
    """
    Cenário: (Modo force_full) Um usuário submete VIRTUAL_WA numa questão do Gym 123. Dias depois, tenta Practice_AC na outra questão do mesmo Gym.
    Resultado Esperado:
    1. A submissão VIRTUAL (antiga na cronologia) gera um ContestParticipation para o Gym 123.
    2. Isso propaga UserProblemTracking Unattempted/PendingTriage para TODAS as outras questões do Gym 123.
    3. Quando o script processa a submissão nova de Practice, ele enxerga o ContestParticipation ligado à prova, blindando-a contra o rebaixamento para PRACTICE_AC e marcando-a como UPSOLVED.
    """
    from api.models import Contest
    
    user = User.objects.create(username="upsolver", cf_handle="upsvr")
    contest = Contest.objects.create(platform=PlatformChoices.CF_GYM, platform_id="100123", name="Gym 123")
    
    prob_a = Problem.objects.create(platform=PlatformChoices.CF_GYM, platform_id="100123A", title="Problema A", contest=contest)
    prob_b = Problem.objects.create(platform=PlatformChoices.CF_GYM, platform_id="100123B", title="Problema B", contest=contest)

    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK', 
            'result': [
                {'id': 200, 'verdict': 'OK', 'creationTimeSeconds': 2000, 'problem': {'contestId': 100123, 'index': 'A'}, 'author': {'participantType': 'PRACTICE'}},
                {'id': 100, 'verdict': 'WRONG_ANSWER', 'creationTimeSeconds': 1000, 'problem': {'contestId': 100123, 'index': 'B'}, 'author': {'participantType': 'VIRTUAL'}} 
            ]
        },
        status=200
    )
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={'status': 'OK', 'result': []},
        status=200
    )
    
    call_command('sync_cf', force_full=True)
    
    assert user.contest_participations.filter(contest=contest).exists(), "Participation não foi criada!"
    
    track_a = UserProblemTracking.objects.get(user=user, problem=prob_a)
    assert track_a.system_status == UserProblemTracking.SystemStatus.UPSOLVED, f"Regra quebrada: O Upsolving AC virou {track_a.system_status}"
    
    track_b = UserProblemTracking.objects.get(user=user, problem=prob_b) 
    assert track_b.system_status == UserProblemTracking.SystemStatus.PENDING_UPSOLVE


@pytest.mark.django_db
@responses.activate
def test_sync_cf_gym_dynamically_fetches_all_problems():
    """
    Cenário: O usuário faz uma submissão num contest Gym que ainda não existe no nosso banco (contestId >= 100000).
    Esperado:
    1. Ao identificar a submissão, o código dinamicamente baterá em 'contest.standings'.
    2. Importará todas as questões originais (A, B, C) desse Gym.
    3. Criará o "ContestParticipation" e a Máquina de Estados blindará a prova inteira para "UNATTEMPTED", mesmo as questões que o usuário nunca submeteu.
    """
    from api.models import Contest, Problem
    user = User.objects.create(username="gym_user", cf_handle="gymmer")

    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 300, 
                    'verdict': 'WRONG_ANSWER', 
                    'creationTimeSeconds': 3000, 
                    'problem': {'contestId': 100124, 'index': 'A', 'name': 'First'}, 
                    'author': {'participantType': 'CONTESTANT'}
                }
            ]
        },
        status=200
    )
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={'status': 'OK', 'result': []},
        status=200
    )
    
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        json={
            'status': 'OK',
            'result': {
                'contest': {'id': 100124, 'name': 'Gym 100124', 'startTimeSeconds': 2000, 'durationSeconds': 7200},
                'problems': [
                    {'contestId': 100124, 'index': 'A', 'name': 'First A', 'rating': 1000},
                    {'contestId': 100124, 'index': 'B', 'name': 'Second B', 'rating': 1200},
                    {'contestId': 100124, 'index': 'C', 'name': 'Third C'}
                ],
                'rows': []
            }
        },
        status=200
    )

    call_command('sync_cf', force_full=True)

    assert Contest.objects.filter(platform_id="100124").exists(), "Gym não foi criado."
    assert Problem.objects.filter(contest__platform_id="100124").count() == 3, "As 3 questões do Gym não foram sincronizadas!"
    assert UserProblemTracking.objects.filter(user=user, problem__contest__platform_id="100124").count() == 3, "Máquina de estados não englobou todas as questões do Gym!"
