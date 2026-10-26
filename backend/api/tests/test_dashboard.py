import pytest
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone
from api.models import User, Problem, Submission, Contest, UserProblemTracking


@pytest.mark.django_db
@pytest.mark.parametrize('instant', ['2026-10-26T01:30:00+00:00', '2024-03-01T01:30:00+00:00'])
def test_dashboard_calendar_uses_sao_paulo_days_and_exact_windows(base_user, monkeypatch, instant):
    # Arrange: UTC is already tomorrow; the user is still on the previous day.
    from api.services import dashboard_service
    now = datetime.fromisoformat(instant)
    monkeypatch.setattr(dashboard_service.timezone, 'now', lambda: now)
    today = timezone.localdate(now)
    local_midnight = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    problem = Problem.objects.create(platform='CF_OFFICIAL', platform_id='dateA', title='Date', platform_metadata={'ai_rating': 1900, 'ai_tags': ['math']})
    UserProblemTracking.objects.create(user=base_user, problem=problem, review_status='DONE')
    timestamps = [now, now - timedelta(minutes=1), local_midnight - timedelta(days=6), local_midnight - timedelta(days=6, microseconds=1), local_midnight - timedelta(days=364), local_midnight - timedelta(days=364, microseconds=1)]
    for index, stamp in enumerate(timestamps):
        Submission.objects.create(user=base_user, problem=problem, platform_submission_id=f'date{index}', verdict='OK', participant_type='PRACTICE', creation_time=stamp)
    # Act
    data = dashboard_service.get_dashboard_stats(base_user)
    # Assert: count accepted submissions, not unique problems, on the local day.
    assert data['reference_date'] == today.isoformat()
    assert data['timezone'] == 'America/Sao_Paulo'
    counts = {row['date']: row['count'] for row in data['heatmap']}
    assert counts[today.isoformat()] == 2
    assert sum(counts.values()) == 5
    assert (today - timedelta(days=365)).isoformat() not in counts
    assert data['last_7_days']['dates'] == [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    assert data['last_7_days']['activity'][0] is True
    assert data['last_7_days']['total_solved'] == 1
    assert data['last_7_days']['average_difficulty'] == 0
    assert data['difficulty_breakdown'] == {}
    assert data['topics'] == []
    assert data['kpis']['streak'] == 1


@pytest.mark.django_db
def test_dashboard_week_does_not_include_eighth_day_and_keeps_rolling_30_days(base_user, monkeypatch):
    # Arrange
    from api.services import dashboard_service
    now = datetime(2026, 10, 5, 15, tzinfo=dt_timezone.utc)
    monkeypatch.setattr(dashboard_service.timezone, 'now', lambda: now)
    problem = Problem.objects.create(platform='CF_OFFICIAL', platform_id='oldA', title='Older')
    for index, stamp in enumerate([now - timedelta(days=6, hours=13), now - timedelta(days=29)]):
        Submission.objects.create(user=base_user, problem=problem, platform_submission_id=f'old{index}', verdict='OK', participant_type='PRACTICE', creation_time=stamp)
    # Act / Assert
    data = dashboard_service.get_dashboard_stats(base_user)
    assert data['last_7_days']['total_solved'] == 0
    assert data['kpis']['solved_this_month'] == 1


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
    assert data['reference_date'] == timezone.localdate().isoformat()
    assert data['timezone'] == 'America/Sao_Paulo'
    assert 'kpis' in data
    assert data['kpis']['total_solved'] == 1
    assert data['kpis']['acceptance_rate'] == 100.0

    assert 'difficulty_breakdown' in data
    assert data['difficulty_breakdown'].get('1200') == 1

    assert 'topics' in data
    assert data['topics'][0]['name'] == 'math'
    assert data['topics'][0]['solved'] == 1
    assert data['topics'][0]['accuracy'] is None

    assert 'heatmap' in data


@pytest.mark.django_db
def test_dashboard_top_15_and_manual_done_do_not_invent_accepted_activity(base_user):
    # Arrange: manual conclusions count towards the existing total, not towards ACs.
    from api.services.dashboard_service import get_dashboard_stats
    for index in range(16):
        problem = Problem.objects.create(platform='CF_OFFICIAL', platform_id=f'topic{index}', title='Topic', platform_metadata={'tags': [f'topic{index}']})
        UserProblemTracking.objects.create(user=base_user, problem=problem, review_status='DONE')
    # Act
    data = get_dashboard_stats(base_user)
    # Assert
    assert data['kpis']['total_solved'] == 16
    assert data['kpis']['streak'] == 0
    assert data['kpis']['max_streak'] == 0
    assert data['heatmap'] == []
    assert len(data['topics']) == 15
    assert data['last_7_days']['activity'] == [False] * 7
