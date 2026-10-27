from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as Row

import pytest

from api.services.contest_results import build_contest_results, cf_submission_timing


START = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def participation(complete=True, virtual=True):
    return Row(user_id=1, is_virtual=virtual, participation_date=START + timedelta(minutes=3),
               results_synced_at=START if complete else None, session_start_time=START,
               contest=Row(start_time=START - timedelta(days=30), duration_seconds=18000))


def submission(sid, verdict, seconds, problem_id=1, **extra):
    return Row(platform_submission_id=str(sid), user_id=extra.get('user_id', 1), problem_id=problem_id,
               verdict=verdict, participant_type=extra.get('participant_type', 'VIRTUAL'),
               creation_time=extra.get('creation_time', START + timedelta(seconds=seconds)),
               relative_time_seconds=extra.get('relative_time_seconds', seconds),
               session_start_time=extra.get('session_start_time', START))


def result(rows, status='UNATTEMPTED', complete=True):
    return build_contest_results(participation(complete), [1, 2], rows, {1: status})[1]


def test_direct_ac_keeps_first_ac_time_and_no_errors():
    value = result([submission(1, 'OK', 181), submission(2, 'OK', 190)])
    assert value['accepted'] is True
    assert value['failed_attempts'] == 0
    assert value['first_ac_seconds'] == 181
    assert value['coverage'] == 'complete'


def test_errors_before_and_after_ac_are_distinct_and_ce_is_not_an_attempt():
    value = result([submission(4, 'WRONG_ANSWER', 500), submission(2, 'TIME_LIMIT_EXCEEDED', 200),
                    submission(1, 'WRONG_ANSWER', 100), submission(3, 'OK', 300),
                    submission(5, 'COMPILATION_ERROR', 50), submission(6, 'TESTING', 60),
                    submission(7, 'FAILED', 70)])
    assert value['failed_attempts'] == 2
    assert value['errors_before_ac'] == {'WA': 1, 'TLE': 1}
    assert value['errors_after_ac'] == {'WA': 1}
    assert value['compilation_errors'] == 1


@pytest.mark.parametrize('verdict,label', [('WRONG_ANSWER', 'WA'), ('RUNTIME_ERROR', 'RE'),
    ('TIME_LIMIT_EXCEEDED', 'TLE'), ('MEMORY_LIMIT_EXCEEDED', 'MLE')])
def test_unsolved_question_counts_judgement_errors(verdict, label):
    value = result([submission(1, verdict, 100)])
    assert value['accepted'] is False
    assert value['failed_attempts'] == 1
    assert value['errors_before_ac'] == {label: 1}
    assert value['first_ac_seconds'] is None


def test_unattempted_and_duplicate_submissions():
    row = submission(1, 'WRONG_ANSWER', 100)
    values = build_contest_results(participation(), [1, 2], [row, row])
    assert values[1]['failed_attempts'] == 1
    assert values[2]['accepted'] is False
    assert values[2]['failed_attempts'] == 0


def test_practice_ac_does_not_rewrite_contest_and_other_sessions_are_excluded():
    value = result([submission(1, 'WRONG_ANSWER', 100),
                    submission(2, 'OK', 20000, participant_type='PRACTICE'),
                    submission(3, 'OK', 100, session_start_time=START + timedelta(days=1),
                               creation_time=START + timedelta(days=1, seconds=100)),
                    submission(4, 'OK', 200, user_id=2)], status='UPSOLVED')
    assert value['accepted'] is False
    assert value['failed_attempts'] == 1
    assert value['is_upsolved'] is True
    assert value['upsolved_at'] is not None
    assert value['manual_completion'] is False


def test_manual_completion_does_not_invent_an_ac():
    value = result([], status='UPSOLVED')
    assert value['accepted'] is False
    assert value['is_upsolved'] is True
    assert value['manual_completion'] is True
    assert value['first_ac_seconds'] is None


def test_virtual_attempt_without_session_metadata_cannot_contaminate_known_session():
    value = result([submission(1, 'WRONG_ANSWER', 100),
                    submission(2, 'OK', 200, relative_time_seconds=None, session_start_time=None)])
    assert value['accepted'] is False
    assert value['first_ac_seconds'] is None
    assert value['errors_before_ac'] == {'WA': 1}
    assert value['failed_attempts'] is None
    assert value['coverage'] == 'partial'


def test_old_or_incomplete_data_never_invents_zero_attempts():
    value = result([submission(1, 'OK', 100)], status='SOLVED_LIVE', complete=False)
    assert value['accepted'] is True
    assert value['failed_attempts'] is None
    assert value['coverage'] == 'partial'


def test_missing_virtual_start_is_not_the_first_submission_time():
    part = participation()
    part.session_start_time = None
    value = build_contest_results(part, [1],
        [submission(1, 'OK', 100, relative_time_seconds=None, session_start_time=None)],
        {1: 'SOLVED_LIVE'})[1]
    assert value['first_ac_seconds'] is None
    assert value['coverage'] == 'partial'


def test_partial_legacy_upsolve_with_imported_ac_is_not_reported_as_manual():
    part = participation(complete=False)
    part.session_start_time = None
    value = build_contest_results(part, [1], [submission(1, 'OK', 20000,
        participant_type='PRACTICE', relative_time_seconds=None, session_start_time=None)],
        {1: 'UPSOLVED'})[1]
    assert value['is_upsolved'] is True
    assert value['manual_completion'] is False
    assert value['upsolved_at'] is None
    assert value['coverage'] == 'partial'


def test_window_end_and_unrelated_participant_types_are_excluded():
    value = result([submission(1, 'OK', 18000), submission(2, 'OK', 100, participant_type='CONTESTANT')])
    assert value['accepted'] is False


def test_cf_timing_uses_virtual_relative_time_not_original_contest():
    raw = {'creationTimeSeconds': int(START.timestamp()) + 181, 'relativeTimeSeconds': 181,
           'author': {'participantType': 'VIRTUAL'}}
    assert cf_submission_timing(raw) == {'relative_time_seconds': 181, 'session_start_time': START}
    assert cf_submission_timing({'creationTimeSeconds': 1}) == {'relative_time_seconds': None, 'session_start_time': None}


def test_cf_timing_rejects_invalid_or_contradictory_metadata():
    raw = {'creationTimeSeconds': int(START.timestamp()) + 100, 'relativeTimeSeconds': -1,
           'author': {'startTimeSeconds': int(START.timestamp())}}
    assert cf_submission_timing(raw)['relative_time_seconds'] is None
    raw['relativeTimeSeconds'] = 300
    assert cf_submission_timing(raw)['session_start_time'] is None


def test_cf_independently_rounded_seconds_keep_the_explicit_party_start():
    raw = {'creationTimeSeconds': int(START.timestamp()) + 182, 'relativeTimeSeconds': 181,
           'author': {'participantType': 'VIRTUAL', 'startTimeSeconds': int(START.timestamp())}}
    assert cf_submission_timing(raw) == {'relative_time_seconds': 181, 'session_start_time': START}
    value = result([submission(1, 'OK', 182, relative_time_seconds=181)])
    assert value['first_ac_seconds'] == 181
    raw['creationTimeSeconds'] += 1
    assert cf_submission_timing(raw)['session_start_time'] is None


def test_last_virtual_second_uses_the_provider_relative_clock():
    value = result([submission(1, 'OK', 18000, relative_time_seconds=17999)])
    assert value['accepted'] is True
    assert value['first_ac_seconds'] == 17999
