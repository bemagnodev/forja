import pytest
from unittest.mock import patch
from io import StringIO
from django.core.management import call_command
import responses
from api.models import User, Problem, Submission, UserProblemTracking, PlatformChoices

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
    # O epoch deve parar no 1200. O 1500 (TESTING) não pode ser o max_epoch
    assert user.cf_last_sync_time == 1200
    
    # Garante que a wall defendeu e ignorou inserts antigos 
    # id 99 (valido) deve estar no banco
    assert Submission.objects.filter(platform_submission_id="99").exists()
    assert UserProblemTracking.objects.filter(problem__platform_id="1B").exists()
    
    # id 98 (antigo, epoch 900) não deve estar gravado no banco pois a wall estava em 1000
    assert not Submission.objects.filter(platform_submission_id="98").exists()
    assert not UserProblemTracking.objects.filter(problem__platform_id="1C").exists()

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
    
    # O epoch do WJ (1500) não deve ter atualizado o atcoder_last_sync_time
    assert user.atcoder_last_sync_time == 1200

    # Verifica o processamento da fila
    # id 99 foi aceito porque epoch 1200 > base 1000
    assert Submission.objects.filter(platform_submission_id="99").exists()
    
    # id 98 descartado porque epoch 900 <= base 1000 (Incremental wall proteged!)
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

@pytest.mark.django_db
@patch('api.services.scrapers.atcoder.AtCoderScraper.scrape')
@patch('api.services.scrapers.atcoder.AtCoderClient.get_problems')
def test_sync_atcoder_endpoint(mock_get_problems, mock_scrape, api_client, base_user):
    # Mock do catálogo de problemas (para o mapeamento de ID -> Título funcionar)
    mock_get_problems.return_value = [
        {"id": "abc100_a", "contest_id": "abc100", "title": "Happy New Year", "name": "Happy New Year"}
    ]
    
    # Simula o retorno do scrape com 1 submissão
    mock_scrape.return_value = {
        "user_handle": "mentor_ac",
        "submissions": [
            {
                "submission_id": "ac_sub_1",
                "problem_id": "abc100_a",
                "contest_id": "abc100",
                "verdict": "AC",
                "creation_time": 1600000000,
            }
        ]
    }
    
    # Testa o endpoint usando o api_client (autenticado)
    resp = api_client.post("/api/sync/atcoder")

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
    
    # Criamos os problemas manualmente pois eles estariam na base caso o metadados já tivesse rodado
    prob_a = Problem.objects.create(platform=PlatformChoices.CF_GYM, platform_id="100123A", title="Problema A", contest=contest)
    prob_b = Problem.objects.create(platform=PlatformChoices.CF_GYM, platform_id="100123B", title="Problema B", contest=contest)

    # API Request simula fila de respostas: 
    # Chamada 1 (from=1) -> Retorna a pagina de resultados
    # Chamada 2 (from=501) -> Retorna array vazio encerrando o loop
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
    
    # 1. Assegurar que 'VIRTUAL' detectou e criou Participation Shield para o contest
    assert user.contest_participations.filter(contest=contest).exists(), "Participation não foi criada!"
    
    # 2. Prova A (Nova Submissão AC): Deve ter lido a participação no passado e processado como UPSOLVED!
    track_a = UserProblemTracking.objects.get(user=user, problem=prob_a)
    assert track_a.system_status == UserProblemTracking.SystemStatus.UPSOLVED, f"Regra quebrada: O Upsolving AC virou {track_a.system_status}"
    
    # 3. Prova B (Antiga Submissão WA): A participação forçou para Pending Upsolve
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

    # MOCK 1: A Submissão do Usuário
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
    # Loop terminator for user.status
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={'status': 'OK', 'result': []},
        status=200
    )
    
    # MOCK 2: O fetch dinâmico do Gym Standings
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

    # Verificaçōes:
    # 1. O Gym inteiro existiu e teve suas 3 questões mapeadas (e não apenas a questão A da submissão).
    assert Contest.objects.filter(platform_id="100124").exists(), "Gym não foi criado."
    assert Problem.objects.filter(contest__platform_id="100124").count() == 3, "As 3 questões do Gym não foram sincronizadas!"
    
    # 2. Como a submissão foi CONTESTANT, o Participation espalhou tracking pra geral
    assert UserProblemTracking.objects.filter(user=user, problem__contest__platform_id="100124").count() == 3, "Máquina de estados não englobou todas as questões do Gym!"
