from datetime import datetime, timedelta, timezone

import pytest
import responses
from django.core.management import call_command
from io import StringIO

from api.models import Contest, ContestParticipation, Problem, Submission, User, UserProblemTracking

START = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


@pytest.fixture
def contest_data(base_user):
    contest = Contest.objects.create(platform='CF_OFFICIAL', platform_id='123', name='Treino',
                                     start_time=START, duration_seconds=7200)
    part = ContestParticipation.objects.create(user=base_user, contest=contest, participation_date=START,
        session_start_time=START, results_synced_at=START)
    a = Problem.objects.create(platform='CF_OFFICIAL', platform_id='123A', title='A', contest=contest)
    b = Problem.objects.create(platform='CF_OFFICIAL', platform_id='123B', title='B', contest=contest)
    return contest, part, a, b


def add_submission(user, problem, sid, verdict, seconds, kind='CONTESTANT'):
    return Submission.objects.create(user=user, problem=problem, platform_submission_id=str(sid),
        verdict=verdict, participant_type=kind, creation_time=START + timedelta(seconds=seconds),
        relative_time_seconds=seconds, session_start_time=START)


@pytest.mark.django_db
def test_api_snapshot_stays_unsolved_after_practice_and_manual_review(api_client, base_user, contest_data):
    contest, _, a, b = contest_data
    add_submission(base_user, a, 1, 'WRONG_ANSWER', 100)
    add_submission(base_user, a, 2, 'OK', 8000, 'PRACTICE')
    tracking = UserProblemTracking.objects.create(user=base_user, problem=a, system_status='UPSOLVED')
    manual = UserProblemTracking.objects.create(user=base_user, problem=b, review_status='DONE')
    before = (tracking.system_status, manual.system_status)
    response = api_client.get(f'/api/contests/{contest.id}/problems')
    assert response.status_code == 200
    values = {p['id']: p for p in response.json()}
    assert values[a.id]['contest_result']['accepted'] is False
    assert values[a.id]['contest_result']['failed_attempts'] == 1
    assert values[a.id]['contest_result']['is_upsolved'] is True
    assert values[b.id]['contest_result']['manual_completion'] is True
    assert values[b.id]['contest_result']['accepted'] is False
    tracking.refresh_from_db()
    manual.refresh_from_db()
    assert before == (tracking.system_status, manual.system_status)


@pytest.mark.django_db
def test_results_never_expose_another_user_or_import_on_read(api_client, contest_data, base_user):
    contest, _, a, _ = contest_data
    other = User.objects.create(username='other')
    add_submission(other, a, 1, 'OK', 100)
    values = api_client.get(f'/api/contests/{contest.id}/problems').json()
    assert values[0]['contest_result']['accepted'] is False
    ContestParticipation.objects.filter(user=base_user).delete()
    assert api_client.get(f'/api/contests/{contest.id}/problems').status_code == 404


@pytest.mark.django_db
def test_list_and_detail_progress_use_the_confirmed_session_without_changing_tracking(api_client, base_user, contest_data):
    contest, part, a, b = contest_data
    part.is_virtual = True
    part.save()
    add_submission(base_user, a, 1, 'WRONG_ANSWER', 100, 'VIRTUAL')
    other_session = add_submission(base_user, a, 2, 'OK', 500, 'VIRTUAL')
    other_session.session_start_time = START + timedelta(seconds=60)
    other_session.save()
    add_submission(base_user, b, 3, 'OK', -100, 'PRACTICE')
    live = UserProblemTracking.objects.create(user=base_user, problem=a, system_status='SOLVED_LIVE')
    practice = UserProblemTracking.objects.create(user=base_user, problem=b, system_status='PRACTICE_AC')

    expected = {'solved_live': 0, 'pending_upsolve': 1, 'upsolved': 0, 'unattempted': 1, 'total': 2}
    assert api_client.get(f'/api/contests/{contest.id}').json()['progress'] == expected
    assert api_client.get('/api/contests').json()[0]['progress'] == expected
    results = {p['id']: p['contest_result'] for p in api_client.get(f'/api/contests/{contest.id}/problems').json()}
    assert results[a.id]['accepted'] is False and results[a.id]['failed_attempts'] == 1
    assert results[b.id]['is_upsolved'] is False
    live.refresh_from_db()
    practice.refresh_from_db()
    assert live.system_status == 'SOLVED_LIVE'
    assert practice.system_status == 'PRACTICE_AC'


@pytest.mark.django_db
@responses.activate
def test_sync_persists_timing_and_complete_history(base_user, contest_data):
    contest, part, a, _ = contest_data
    responses.get('https://codeforces.com/api/user.status', json={'status': 'OK', 'result': [
        {'id': 2, 'verdict': 'OK', 'creationTimeSeconds': int(START.timestamp()) + 300,
         'relativeTimeSeconds': 300, 'author': {'participantType': 'CONTESTANT'},
         'problem': {'contestId': 123, 'index': 'A'}},
    ]})
    responses.get('https://codeforces.com/api/user.status', json={'status': 'OK', 'result': []})
    call_command('sync_cf', handle=base_user.cf_handle)
    row = Submission.objects.get(platform_submission_id='2')
    assert row.relative_time_seconds == 300
    assert row.session_start_time == START
    part.refresh_from_db()
    assert part.results_synced_at is not None


@pytest.mark.django_db
@responses.activate
def test_hydration_does_not_claim_coverage_if_source_has_unimported_attempts(base_user, contest_data):
    _, part, a, _ = contest_data
    add_submission(base_user, a, 12, 'OK', 300)
    rows = [{'id': sid, 'creationTimeSeconds': int(START.timestamp()) + seconds,
        'relativeTimeSeconds': seconds, 'author': {'participantType': 'CONTESTANT'},
        'verdict': verdict, 'problem': {'contestId': 123, 'index': 'A'}}
        for sid, seconds, verdict in [(12, 300, 'OK'), (11, 100, 'WRONG_ANSWER')]]
    responses.get('https://codeforces.com/api/user.status', json={'status': 'OK', 'result': rows})
    responses.get('https://codeforces.com/api/user.status', json={'status': 'OK', 'result': []})
    responses.get('https://codeforces.com/api/contest.standings', json={'status': 'OK', 'result': {'rows': []}})
    call_command('hydrate_cf_contest_stats', handle=base_user.cf_handle, contest_id=123, apply=True, stdout=StringIO())
    part.refresh_from_db()
    assert part.results_synced_at is None


@pytest.mark.django_db
@responses.activate
def test_hydration_network_failure_keeps_existing_metadata(base_user, contest_data):
    from django.core.management.base import CommandError
    _, part, a, _ = contest_data
    row = add_submission(base_user, a, 12, 'OK', 300)
    responses.get('https://codeforces.com/api/user.status', status=503)
    with pytest.raises(CommandError):
        call_command('hydrate_cf_contest_stats', handle=base_user.cf_handle, contest_id=123, apply=True)
    row.refresh_from_db()
    part.refresh_from_db()
    assert row.relative_time_seconds == 300
    assert part.results_synced_at == START


@pytest.mark.django_db
@responses.activate
def test_hydration_accepts_independently_rounded_seconds(base_user, contest_data):
    _, part, a, _ = contest_data
    part.is_virtual = True
    part.results_synced_at = None
    part.save()
    add_submission(base_user, a, 1, 'WRONG_ANSWER', 101, 'VIRTUAL')
    add_submission(base_user, a, 2, 'OK', 302, 'VIRTUAL')
    rows = [{'id': sid, 'creationTimeSeconds': int(START.timestamp()) + seconds,
        'relativeTimeSeconds': seconds - 1, 'author': {'participantType': 'VIRTUAL', 'startTimeSeconds': int(START.timestamp())},
        'verdict': verdict, 'problem': {'contestId': 123, 'index': 'A'}}
        for sid, seconds, verdict in [(2, 302, 'OK'), (1, 101, 'WRONG_ANSWER')]]
    responses.get('https://codeforces.com/api/user.status', json={'status': 'OK', 'result': rows})
    responses.get('https://codeforces.com/api/user.status', json={'status': 'OK', 'result': []})
    call_command('hydrate_cf_contest_stats', handle=base_user.cf_handle, contest_id=123, apply=True, stdout=StringIO())
    part.refresh_from_db()
    assert part.results_synced_at is not None
    from api.services.contest_results import contest_results
    result = contest_results(part, [a])[a.id]
    assert result['failed_attempts'] == 1
    assert result['first_ac_seconds'] == 301


@pytest.mark.django_db
@responses.activate
def test_hydration_defaults_to_preview_and_only_updates_metadata(base_user, contest_data):
    contest, part, a, _ = contest_data
    row = add_submission(base_user, a, 12, 'OK', 300)
    Submission.objects.filter(pk=row.pk).update(relative_time_seconds=None, session_start_time=None)
    part.results_synced_at = None
    part.save()
    tracking = UserProblemTracking.objects.create(user=base_user, problem=a, system_status='PENDING_UPSOLVE')
    raw = {'status': 'OK', 'result': [{'id': 12, 'creationTimeSeconds': int(START.timestamp()) + 300,
        'relativeTimeSeconds': 300, 'author': {'participantType': 'CONTESTANT'},
        'verdict': 'OK', 'problem': {'contestId': 123, 'index': 'A'}}]}
    responses.get('https://codeforces.com/api/user.status', json=raw)
    responses.get('https://codeforces.com/api/user.status', json={'status': 'OK', 'result': []})
    output = StringIO()
    call_command('hydrate_cf_contest_stats', handle=base_user.cf_handle, contest_id=123, stdout=output)
    row.refresh_from_db()
    assert row.relative_time_seconds is None
    assert 'prévia' in output.getvalue().lower()
    responses.get('https://codeforces.com/api/user.status', json=raw)
    responses.get('https://codeforces.com/api/user.status', json={'status': 'OK', 'result': []})
    responses.get('https://codeforces.com/api/contest.standings', json={'status': 'OK', 'result': {
        'contest': {'type': 'ICPC'}, 'rows': [{'rank': 11, 'penalty': 700, 'party': {
            'participantType': 'CONTESTANT', 'members': [{'handle': base_user.cf_handle}]}}]}})
    call_command('hydrate_cf_contest_stats', handle=base_user.cf_handle, contest_id=123, apply=True, stdout=output)
    row.refresh_from_db()
    tracking.refresh_from_db()
    base_user.refresh_from_db()
    part.refresh_from_db()
    assert row.relative_time_seconds == 300
    assert tracking.system_status == 'PENDING_UPSOLVE'
    assert base_user.cf_last_sync_time is None
    assert part.rank == 11 and part.penalty == 700 and part.rank_context == 'OFFICIAL'
    assert part.results_synced_at is not None
