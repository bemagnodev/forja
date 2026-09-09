import pytest
from django.utils import timezone
from api.models import User, Problem, Submission, Contest, UserProblemTracking


@pytest.mark.django_db
def test_dashboard_stats_endpoint(api_client, base_user):
    """
    Cenário: Requisição para /api/dashboard/stats por usuário autenticado com histórico de submissões e tracking.
    Resultado esperado: Retorno de KPIs (total_solved, acceptance_rate), breakdown de dificuldade e tópicos.
    """
    c = Contest.objects.create(platform='CF_OFFICIAL', platform_id='1000', name='Test Contest')
    p = Problem.objects.create(
        platform='CF_OFFICIAL',
        platform_id='1000A',
        title='Test Problem',
        contest=c,
        platform_metadata={'rating': 1200, 'tags': ['math']}
    )

    UserProblemTracking.objects.create(
        user=base_user,
        problem=p,
        system_status='SOLVED_LIVE',
        review_status='DONE'
    )

    Submission.objects.create(
        platform_submission_id='sub1',
        user=base_user,
        problem=p,
        participant_type='CONTESTANT',
        verdict='OK',
        creation_time=timezone.now()
    )

    url = '/api/dashboard/stats'
    response = api_client.get(url)
    assert response.status_code == 200

    data = response.json()
    assert 'kpis' in data
    assert data['kpis']['total_solved'] == 1
    assert data['kpis']['acceptance_rate'] == 100.0

    assert 'difficulty_breakdown' in data
    assert data['difficulty_breakdown'].get('1200') == 1

    assert 'topics' in data
    assert data['topics'][0]['name'] == 'math'

    assert 'heatmap' in data
