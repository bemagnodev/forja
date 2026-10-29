import sqlite3

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, Client

from api.visual_preview import copy_database, PreviewNetworkGuard


def test_preview_backup_is_independent_and_never_overwrites(tmp_path):
    source = tmp_path / 'original.sqlite3'
    with sqlite3.connect(source) as db:
        db.execute('create table evidence (value text)')
        db.execute("insert into evidence values ('original')")
    target = tmp_path / 'preview' / 'preview.sqlite3'
    copy_database(source, target, target.parent)
    with sqlite3.connect(target) as db:
        db.execute("update evidence set value='local'")
    with sqlite3.connect(source) as db:
        assert db.execute('select value from evidence').fetchone() == ('original',)
    with pytest.raises(ValueError, match='exist'):
        copy_database(source, target, target.parent)
    with pytest.raises(ValueError):
        copy_database(source, source, target.parent)
    with pytest.raises(ValueError):
        copy_database(source, tmp_path / 'outside.sqlite3', target.parent)


@pytest.mark.parametrize('path', ['/api/sync/cf', '/api/sync/atcoder', '/api/problems/1/predict'])
def test_preview_blocks_external_mutations_before_handler(path, settings):
    settings.VISUAL_PREVIEW = True
    calls = []
    guard = PreviewNetworkGuard(lambda request: calls.append(request) or HttpResponse('called'))
    response = guard(RequestFactory().post(path))
    assert response.status_code == 403
    assert not calls


def test_preview_keeps_local_crud_and_saved_benchmarks(settings):
    settings.VISUAL_PREVIEW = True
    guard = PreviewNetworkGuard(lambda request: HttpResponse('local'))
    for method, path in [('post', '/api/queue'), ('get', '/api/ai-lab/benchmarks')]:
        assert guard(getattr(RequestFactory(), method)(path)).status_code == 200


@pytest.mark.django_db
def test_preview_explore_requires_auth_and_uses_no_provider(api_client, client, sample_problem, settings, monkeypatch):
    import api.api as endpoints
    settings.VISUAL_PREVIEW = True
    monkeypatch.setattr(endpoints, '_classify_for_ui', lambda *args: pytest.fail('provider called'))
    path = f'/api/ai-lab/problems/{sample_problem.id}/classify'
    assert Client().post(path).status_code == 401
    response = api_client.post(path + '?preview_scenario=success')
    assert response.status_code == 200
    assert response.json()['rating'] == 1600
    assert 'Simulação local' in response.json()['reasoning']
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata == {}
    assert api_client.post(path).status_code == 400
    assert api_client.post(path + '?preview_scenario=error').status_code == 502
    settings.VISUAL_PREVIEW = False
    assert api_client.post(path + '?preview_scenario=success').status_code == 400


@pytest.mark.django_db
def test_qa_seed_covers_complete_partial_manual_and_empty_accounts(settings):
    from api.management.commands.prepare_visual_preview import seed_qa_cases
    from api.models import ContestParticipation, Submission, UserProblemTracking, QueueItem, User
    settings.VISUAL_PREVIEW = False
    with pytest.raises(ValueError):
        seed_qa_cases()
    assert User.objects.count() == 0
    settings.VISUAL_PREVIEW = True
    seed_qa_cases()
    qa = User.objects.get(username='preview_qa')
    assert ContestParticipation.objects.filter(user=qa, results_synced_at__isnull=False).exists()
    assert ContestParticipation.objects.filter(user=qa, results_synced_at__isnull=True).exists()
    assert ContestParticipation.objects.filter(user=qa, rank__isnull=True).exists()
    assert Submission.objects.filter(user=qa, verdict='OK').exists()
    manual = UserProblemTracking.objects.get(user=qa, problem__platform_id='999900O')
    assert manual.system_status == 'UPSOLVED'
    assert manual.review_status == 'DONE'
    assert not Submission.objects.filter(user=qa, problem=manual.problem).exists()
    empty = User.objects.get(username='preview_empty')
    assert not QueueItem.objects.filter(user=empty).exists()
    assert not ContestParticipation.objects.filter(user=empty).exists()


@pytest.mark.django_db
@pytest.mark.parametrize('scenario,expected', [('exact', 1400), ('overestimate', 1600), ('underestimate', 1200)])
def test_preview_comparison_scenarios_keep_the_real_reference(api_client, sample_problem, settings, scenario, expected):
    settings.VISUAL_PREVIEW = True
    sample_problem.platform_metadata = {'rating': 1400, 'tags': ['math']}
    sample_problem.save()
    response = api_client.post(f'/api/ai-lab/problems/{sample_problem.id}/classify?preview_scenario={scenario}')
    assert response.status_code == 200
    assert response.json()['real_rating'] == 1400
    assert response.json()['rating'] == expected
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata == {'rating': 1400, 'tags': ['math']}


@pytest.mark.django_db
def test_qa_contest_has_distinct_plus_attempts_and_compilation_cases(settings):
    from api.management.commands.prepare_visual_preview import seed_qa_cases
    from api.models import ContestParticipation, Submission, Problem
    from api.services.contest_results import build_contest_results
    settings.VISUAL_PREVIEW = True
    seed_qa_cases()
    part = ContestParticipation.objects.get(user__username='preview_qa', contest__platform_id='999900')
    problems = {p.platform_id: p.id for p in Problem.objects.filter(contest=part.contest)}
    results = build_contest_results(part, problems.values(), Submission.objects.filter(user=part.user))
    assert results[problems['999900A']]['failed_attempts'] == 0
    assert results[problems['999900B']]['failed_attempts'] == 2
    assert results[problems['999900C']]['compilation_errors'] == 1
