import pytest
import responses
from django.core.management import call_command
from api.models import User, Problem, Submission, UserProblemTracking, PlatformChoices, Contest, ContestParticipation


def create_gym_standings_mock(contest_id="106682", name="2026 Argentinian Programming Tournament (TAP)", num_problems=14):
    """
    Gera a estrutura mockada de contest.standings do Codeforces Gym
    com os 14 problemas clássicos de A até N.
    """
    letters = [chr(ord('A') + i) for i in range(num_problems)]
    problems_data = [
        {
            'contestId': int(contest_id),
            'index': letter,
            'name': f"Problem {letter}",
            'rating': 1000 + (i * 100),
            'tags': ['implementation'] if i == 0 else ['dp', 'math']
        }
        for i, letter in enumerate(letters)
    ]
    return {
        'status': 'OK',
        'result': {
            'contest': {
                'id': int(contest_id),
                'name': name,
                'startTimeSeconds': 1760000000,
                'durationSeconds': 18000
            },
            'problems': problems_data,
            'rows': []
        }
    }


@pytest.mark.django_db
@responses.activate
def test_sync_cf_updates_existing_incomplete_gym():
    """
    Cenário A: Gym já existente, porém incompleto.
    Dado um Contest Gym já salvo no banco, mas com nome desatualizado e sem catálogo de problemas.
    Ao executar o sync, o contest deve ser atualizado com os metadados oficiais,
    todos os 14 problemas (A-N) devem ser criados/atualizados, sem duplicar o Contest.
    """
    user = User.objects.create(username="bemagno", cf_handle="bemagno")
    
    # Contest pré-existente com metadados incompletos/placeholders
    Contest.objects.create(
        platform=PlatformChoices.CF_GYM,
        platform_id="106682",
        name="Gym 106682",
        duration_seconds=0
    )

    # Submissão do usuário em uma questão do Gym
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 5001,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1760001000,
                    'problem': {'contestId': 106682, 'index': 'A', 'name': 'Problem A'},
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

    # Mock dos metadados completos do Gym 106682 com 14 problemas (A até N)
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        json=create_gym_standings_mock(contest_id="106682"),
        status=200
    )

    call_command('sync_cf', force_full=True)

    # 1. Não duplicou o contest
    assert Contest.objects.filter(platform=PlatformChoices.CF_GYM, platform_id="106682").count() == 1
    
    # 2. Metadados do contest foram atualizados
    contest = Contest.objects.get(platform=PlatformChoices.CF_GYM, platform_id="106682")
    assert contest.name == "2026 Argentinian Programming Tournament (TAP)"
    assert contest.duration_seconds == 18000

    # 3. Todos os 14 problemas existem no banco e vinculados a este contest
    problems = Problem.objects.filter(contest=contest)
    assert problems.count() == 14
    expected_indices = {chr(ord('A') + i) for i in range(14)}
    actual_indices = {p.platform_id.replace("106682", "") for p in problems}
    assert actual_indices == expected_indices


@pytest.mark.django_db
@responses.activate
def test_sync_cf_force_full_recovers_participation_behind_watermark(api_client):
    """
    Cenário B: Participação anterior ao watermark.
    Dado um usuário cujo cf_last_sync_time é mais recente que a data do Gym.
    O sync incremental comum respeita a barreira temporal e ignora a submissão.
    O sync com --force-full recupera a submissão e a participação passa a constar
    no endpoint de contests.
    """
    user = User.objects.get(username="mentor")
    user.cf_last_sync_time = 1800000000  # Watermark à frente das submissões do Gym
    user.save()

    submission_data = {
        'id': 6001,
        'verdict': 'OK',
        'creationTimeSeconds': 1760002000,  # Anterior ao watermark (1800000000)
        'problem': {'contestId': 106682, 'index': 'A', 'name': 'Problem A'},
        'author': {'participantType': 'CONTESTANT'}
    }

    # Resposta de user.status para o sync incremental
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={'status': 'OK', 'result': [submission_data]},
        status=200
    )

    # 1. Execução do sync incremental
    call_command('sync_cf')

    # Como a submissão é anterior ao watermark, ContestParticipation não deve existir
    assert not ContestParticipation.objects.filter(user=user, contest__platform_id="106682").exists()

    # Agora preparamos as respostas para o --force-full
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={'status': 'OK', 'result': [submission_data]},
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
        json=create_gym_standings_mock(contest_id="106682"),
        status=200
    )

    # 2. Execução com --force-full
    call_command('sync_cf', force_full=True)

    # Confirma que a participação foi recuperada
    assert ContestParticipation.objects.filter(user=user, contest__platform_id="106682").exists()

    # Confirma que a participação aparece no endpoint /api/contests
    resp = api_client.get("/api/contests")
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["contest_name"] == "2026 Argentinian Programming Tournament (TAP)" for c in data)


@pytest.mark.django_db
@responses.activate
def test_sync_cf_gym_idempotency():
    """
    Cenário C: Idempotência da sincronização.
    Executar a sincronização duas vezes consecutivas com os mesmos dados mockados
    não duplica Contest, Problem, Submission, ContestParticipation ou UserProblemTracking.
    """
    user = User.objects.create(username="idemp_user", cf_handle="idemp_handle")

    sub_mock = [
        {
            'id': 7001,
            'verdict': 'OK',
            'creationTimeSeconds': 1760001000,
            'problem': {'contestId': 106682, 'index': 'A', 'name': 'Problem A'},
            'author': {'participantType': 'CONTESTANT'}
        }
    ]

    for _ in range(2):
        responses.add(
            responses.GET,
            'https://codeforces.com/api/user.status',
            json={'status': 'OK', 'result': sub_mock},
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
            json=create_gym_standings_mock(contest_id="106682"),
            status=200
        )

    # Primeira execução
    call_command('sync_cf', force_full=True)

    c_count1 = Contest.objects.filter(platform=PlatformChoices.CF_GYM, platform_id="106682").count()
    p_count1 = Problem.objects.filter(contest__platform_id="106682").count()
    s_count1 = Submission.objects.filter(platform_submission_id="7001").count()
    cp_count1 = ContestParticipation.objects.filter(user=user, contest__platform_id="106682").count()
    upt_count1 = UserProblemTracking.objects.filter(user=user, problem__contest__platform_id="106682").count()

    assert c_count1 == 1
    assert p_count1 == 14
    assert s_count1 == 1
    assert cp_count1 == 1
    assert upt_count1 == 14

    # Segunda execução
    call_command('sync_cf', force_full=True)

    assert Contest.objects.filter(platform=PlatformChoices.CF_GYM, platform_id="106682").count() == c_count1
    assert Problem.objects.filter(contest__platform_id="106682").count() == p_count1
    assert Submission.objects.filter(platform_submission_id="7001").count() == s_count1
    assert ContestParticipation.objects.filter(user=user, contest__platform_id="106682").count() == cp_count1
    assert UserProblemTracking.objects.filter(user=user, problem__contest__platform_id="106682").count() == upt_count1


@pytest.mark.django_db
@responses.activate
def test_sync_cf_identifies_contest_by_platform_and_id():
    """
    Cenário D: Identificação por plataforma e ID.
    Caso exista um Contest oficial com o mesmo platform_id de um Gym, a sincronização
    não deve confundir ou vincular problemas do Gym ao Contest oficial.
    """
    user = User.objects.create(username="plat_user", cf_handle="plat_handle")

    # Contest oficial com mesmo ID numérico (ex: 106682)
    official_contest = Contest.objects.create(
        platform=PlatformChoices.CF_OFFICIAL,
        platform_id="106682",
        name="Official Codeforces Round 106682"
    )

    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 8001,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1760001000,
                    'problem': {'contestId': 106682, 'index': 'A', 'name': 'Problem A'},
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
        json=create_gym_standings_mock(contest_id="106682"),
        status=200
    )

    call_command('sync_cf', force_full=True)

    # Deve existir o Contest CF_OFFICIAL intacto e um novo Contest CF_GYM
    assert Contest.objects.filter(platform=PlatformChoices.CF_OFFICIAL, platform_id="106682").count() == 1
    assert Contest.objects.filter(platform=PlatformChoices.CF_GYM, platform_id="106682").count() == 1

    gym_contest = Contest.objects.get(platform=PlatformChoices.CF_GYM, platform_id="106682")
    problem_a = Problem.objects.get(platform=PlatformChoices.CF_GYM, platform_id="106682A")

    # O problema do Gym deve apontar para o contest do Gym, não para o oficial
    assert problem_a.contest == gym_contest
    assert problem_a.contest != official_contest


@pytest.mark.django_db
@responses.activate
def test_sync_cf_gym_dashboard_integration(api_client):
    """
    Cenário E: Integração completa com o endpoint de Contests do Dashboard.
    Após a sincronização do Gym 106682, o endpoint /api/contests deve retornar
    o Gym com nome correto, plataforma CF_GYM, total de 14 problemas e progresso condizente.
    """
    user = User.objects.get(username="mentor")

    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 9001,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1760002000,
                    'problem': {'contestId': 106682, 'index': 'A', 'name': 'Problem A'},
                    'author': {'participantType': 'CONTESTANT'}
                },
                {
                    'id': 9002,
                    'verdict': 'WRONG_ANSWER',
                    'creationTimeSeconds': 1760003000,
                    'problem': {'contestId': 106682, 'index': 'B', 'name': 'Problem B'},
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
        json=create_gym_standings_mock(contest_id="106682"),
        status=200
    )

    call_command('sync_cf', force_full=True)

    resp = api_client.get("/api/contests")
    assert resp.status_code == 200
    data = resp.json()
    
    gym_entry = next((item for item in data if item["contest_name"] == "2026 Argentinian Programming Tournament (TAP)"), None)
    assert gym_entry is not None, "Gym 106682 não foi encontrado na resposta de /api/contests"

    assert gym_entry["contest_platform"] == PlatformChoices.CF_GYM
    assert gym_entry["progress"]["total"] == 14
    assert gym_entry["progress"]["solved_live"] == 1
    assert gym_entry["progress"]["pending_upsolve"] == 1
    assert gym_entry["progress"]["unattempted"] == 12
    assert gym_entry["has_debt"] is True


@pytest.mark.django_db
@responses.activate
def test_sync_cf_gym_metadata_failure_preserves_watermark():
    """
    Cenário F: Falha na obtenção dos metadados do Gym.
    Se a API do Codeforces falhar ao buscar metadados de um Gym (ex: HTTP 500 ou indisponibilidade),
    o watermark não deve avançar indevidamente consumindo a submissão, permitindo que a próxima
    execução incremental tente reparar e buscar os dados novamente.
    """
    user = User.objects.create(username="fail_user", cf_handle="fail_handle", cf_last_sync_time=1000)

    # Submissão em 1500
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 9501,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1500,
                    'problem': {'contestId': 106682, 'index': 'A', 'name': 'Problem A'},
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

    # Falha transitória na API do Codeforces ao buscar contest.standings (ex: 500 Internal Server Error)
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=500,
        body="Internal Server Error"
    )

    call_command('sync_cf')

    user.refresh_from_db()
    # O watermark não deve ter avançado para 1500, preservando a tentativa para o próximo sync
    assert user.cf_last_sync_time == 1000


@pytest.mark.django_db
@responses.activate
def test_sync_cf_partial_failure_does_not_advance_watermark_past_failed_submission():
    """
    Cenário: Falha parcial no lote de submissões.
    Dado um histórico com duas submissões mais recentes que o watermark (1000):
    - Submissão 1 (epoch 1500, Gym 106682): falha ao obter metadados do Gym.
    - Submissão 2 (epoch 2000, Contest Oficial 1): processada com sucesso.
    Esperado:
    O watermark NÃO avança para 2000 (nem ultrapassa a submissão que falhou em 1500),
    permanecendo em 1000 para que a próxima execução reavalie todo o histórico pendente.
    """
    user = User.objects.create(username="partial_fail_user", cf_handle="partial_fail", cf_last_sync_time=1000)

    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 9602,
                    'verdict': 'OK',
                    'creationTimeSeconds': 2000,
                    'problem': {'contestId': 1, 'index': 'A', 'name': 'Official Problem A'},
                    'author': {'participantType': 'PRACTICE'}
                },
                {
                    'id': 9601,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1500,
                    'problem': {'contestId': 106682, 'index': 'A', 'name': 'Gym Problem A'},
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

    # Falha na API do Codeforces ao buscar contest.standings do Gym
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        json={'status': 'FAILED', 'comment': 'Gym not available'},
        status=200
    )

    call_command('sync_cf')

    user.refresh_from_db()
    # Como uma submissão necessária do lote falhou, o watermark não deve avançar para 2000
    assert user.cf_last_sync_time == 1000


@pytest.mark.django_db
@responses.activate
def test_sync_cf_submission_preserves_catalog_metadata_rating_and_tags():
    """
    Cenário: Preservação de metadados do catálogo de problemas.
    O catálogo do Gym importa o problema A com rating 1600 e tags ['dp', 'greedy'].
    A submissão em user.status vem sem rating e sem tags (comum no Codeforces para Gyms).
    O processamento da submissão NÃO deve sobrescrever ou apagar o rating/tags do catálogo.
    """
    user = User.objects.create(username="meta_user", cf_handle="meta_handle")

    # Submissão em user.status sem rating e sem tags
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 9701,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1760002000,
                    'problem': {
                        'contestId': 106682,
                        'index': 'A',
                        'name': 'Problem A'
                        # Notar: sem 'rating' e sem 'tags'
                    },
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

    # Catálogo oficial do Gym com rating e tags definidos
    gym_mock = create_gym_standings_mock(contest_id="106682")
    gym_mock['result']['problems'][0]['rating'] = 1600
    gym_mock['result']['problems'][0]['tags'] = ['dp', 'greedy']

    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        json=gym_mock,
        status=200
    )

    call_command('sync_cf', force_full=True)

    prob_a = Problem.objects.get(platform=PlatformChoices.CF_GYM, platform_id="106682A")
    assert prob_a.platform_metadata.get('rating') == 1600, "Rating do catálogo foi apagado pelo sync da submissão!"
    assert prob_a.platform_metadata.get('tags') == ['dp', 'greedy'], "Tags do catálogo foram apagadas pelo sync da submissão!"


@pytest.mark.django_db
@responses.activate
def test_sync_cf_attempts_gym_only_once_per_run_even_with_multiple_submissions():
    """
    Parte 2: Uma tentativa por Gym em cada execução.
    Dado um histórico com múltiplas submissões apontando para o mesmo Gym inacessível (ex: HTTP 400).
    Esperado:
    - contest.standings é chamado exatamente UMA vez para aquele Gym;
    - as submissões seguintes daquele mesmo Gym não repetem a chamada à API;
    - outro Gym acessível ainda pode ser consultado normalmente.
    """
    user = User.objects.create(username="repeat_user", cf_handle="repeat_handle")

    # Três submissões do Gym inacessível 109999 e uma do Gym acessível 106682
    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 101,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1760003000,
                    'problem': {'contestId': 106682, 'index': 'A', 'name': 'Accessible A'},
                    'author': {'participantType': 'CONTESTANT'}
                },
                {
                    'id': 102,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1760002000,
                    'problem': {'contestId': 109999, 'index': 'B', 'name': 'Private B'},
                    'author': {'participantType': 'CONTESTANT'}
                },
                {
                    'id': 103,
                    'verdict': 'WRONG_ANSWER',
                    'creationTimeSeconds': 1760001500,
                    'problem': {'contestId': 109999, 'index': 'A', 'name': 'Private A'},
                    'author': {'participantType': 'CONTESTANT'}
                },
                {
                    'id': 104,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1760001000,
                    'problem': {'contestId': 109999, 'index': 'A', 'name': 'Private A'},
                    'author': {'participantType': 'CONTESTANT'}
                },
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

    # Mock do Gym 109999 inacessível (HTTP 400)
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=400,
        body="Contest is not visible"
    )

    # Mock do Gym 106682 acessível
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        json=create_gym_standings_mock(contest_id="106682"),
        status=200
    )

    call_command('sync_cf', force_full=True)

    # Verifica quantas chamadas foram feitas para contest.standings
    standings_calls = [c for c in responses.calls if "contest.standings" in c.request.url]
    calls_109999 = [c for c in standings_calls if "contestId=109999" in c.request.url]
    calls_106682 = [c for c in standings_calls if "contestId=106682" in c.request.url]

    assert len(calls_109999) == 1, f"O Gym inacessível foi chamado {len(calls_109999)} vezes! Deveria ter sido chamado exatamente 1 vez."
    assert len(calls_106682) == 1, "O Gym acessível deveria ter sido chamado normalmente uma vez."


@pytest.mark.django_db
@responses.activate
def test_sync_cf_transient_failure_retains_watermark():
    """
    Parte 3: Falha transitória (timeout/5xx) retém o watermark.
    Não há dados locais para o Gym e a API retorna erro 500 (transitório).
    A submissão não deve ser consumida definitivamente e o watermark deve ser retido.
    """
    user = User.objects.create(username="transient_user", cf_handle="transient_handle", cf_last_sync_time=1000)

    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 201,
                    'verdict': 'OK',
                    'creationTimeSeconds': 1500,
                    'problem': {'contestId': 105555, 'index': 'A', 'name': 'Problem A'},
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

    # Erro transitório 500
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=500,
        body="Internal Server Error"
    )

    call_command('sync_cf')

    user.refresh_from_db()
    assert user.cf_last_sync_time == 1000, "O watermark avançou indevidamente após falha transitória (500)!"


@pytest.mark.django_db
@responses.activate
def test_sync_cf_private_gym_permanent_failure_fallback_and_dashboard_integration(api_client):
    """
    Parte 4: Fallback para Gym privado / permanentemente indisponível.
    Quando user.status comprova submissões em um Gym privado (HTTP 400):
    - Cria Contest provisório '(CF_GYM, 107777)' com nome 'Gym 107777';
    - Cria apenas os problemas conhecidos pelas submissões (ex: A e B);
    - Salva Submission;
    - Cria ContestParticipation (CONTESTANT);
    - Cria UserProblemTracking correspondente;
    - Não congela o watermark (permite avanço já que o erro é permanente);
    - O Gym aparece no endpoint /api/contests com catálogo parcial.
    """
    user = User.objects.get(username="mentor")
    user.cf_handle = "private_gym_user"
    user.cf_last_sync_time = 1000
    user.save()

    responses.add(
        responses.GET,
        'https://codeforces.com/api/user.status',
        json={
            'status': 'OK',
            'result': [
                {
                    'id': 302,
                    'verdict': 'OK',
                    'creationTimeSeconds': 2000,
                    'problem': {'contestId': 107777, 'index': 'B', 'name': 'Known Prob B'},
                    'author': {'participantType': 'CONTESTANT'}
                },
                {
                    'id': 301,
                    'verdict': 'WRONG_ANSWER',
                    'creationTimeSeconds': 1500,
                    'problem': {'contestId': 107777, 'index': 'A', 'name': 'Known Prob A'},
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

    # HTTP 400 permanente (Gym privado/não visível)
    responses.add(
        responses.GET,
        'https://codeforces.com/api/contest.standings',
        status=400,
        body="Contest is not visible"
    )

    call_command('sync_cf')

    user.refresh_from_db()
    # 1. O watermark pôde avançar para 2000 (não congelou para sempre por causa de erro permanente)
    assert user.cf_last_sync_time == 2000

    # 2. Contest provisório foi criado com nome previsível
    contest = Contest.objects.get(platform=PlatformChoices.CF_GYM, platform_id="107777")
    assert contest.name == "Gym 107777"

    # 3. Apenas os problemas conhecidos (A e B) foram criados (não inventou outros)
    problems = Problem.objects.filter(contest=contest)
    assert set(problems.values_list('platform_id', flat=True)) == {"107777A", "107777B"}

    # 4. Participação foi registrada
    assert ContestParticipation.objects.filter(user=user, contest=contest).exists()

    # 5. Trackings foram criados
    assert UserProblemTracking.objects.filter(user=user, problem__platform_id="107777B", system_status=UserProblemTracking.SystemStatus.SOLVED_LIVE).exists()
    assert UserProblemTracking.objects.filter(user=user, problem__platform_id="107777A", system_status=UserProblemTracking.SystemStatus.PENDING_UPSOLVE).exists()

    # 6. Opção B: O Gym provisório/privado é salvo no banco, mas omitido da listagem em /api/contests
    # Criamos também um Gym público completo para comprovar que ele continua aparecendo normalmente
    public_contest = Contest.objects.create(
        platform=PlatformChoices.CF_GYM,
        platform_id="106682",
        name="2026 Argentinian Programming Tournament (TAP)",
        duration_seconds=18000
    )
    ContestParticipation.objects.create(user=user, contest=public_contest)

    resp = api_client.get("/api/contests")
    assert resp.status_code == 200
    data = resp.json()

    # O Gym provisório com nome "Gym 107777" NÃO deve aparecer na listagem
    item_private = next((c for c in data if c["contest_name"] == "Gym 107777"), None)
    assert item_private is None, "Gym privado provisório não deveria aparecer na listagem de /api/contests!"

    # O Gym público com metadados/nome real DEVE aparecer na listagem
    item_public = next((c for c in data if c["contest_name"] == "2026 Argentinian Programming Tournament (TAP)"), None)
    assert item_public is not None, "Gym público deveria continuar aparecendo em /api/contests!"
