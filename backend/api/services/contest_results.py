"""Read-only contest snapshots. Review/triage and its state machine stay independent."""
from collections import Counter
from datetime import datetime, timedelta, timezone


ERROR_VERDICTS = {
    'WRONG_ANSWER': 'WA', 'RUNTIME_ERROR': 'RE', 'TIME_LIMIT_EXCEEDED': 'TLE',
    'MEMORY_LIMIT_EXCEEDED': 'MLE', 'IDLENESS_LIMIT_EXCEEDED': 'ILE',
    'SECURITY_VIOLATED': 'SEC', 'CRASHED': 'CRASH', 'CHALLENGED': 'CHALLENGED',
}


def cf_submission_timing(raw):
    """Never substitute first submission time for the start of a virtual session."""
    empty = {'relative_time_seconds': None, 'session_start_time': None}
    relative = raw.get('relativeTimeSeconds')
    epoch = raw.get('creationTimeSeconds')
    explicit = raw.get('author', {}).get('startTimeSeconds')
    if type(relative) is not int or relative < 0 or type(epoch) is not int:
        return empty
    # The API independently rounds absolute and relative seconds. Prefer Party's
    # stable start for the session, tolerating only that one-second difference.
    if type(explicit) is int and abs(explicit - (epoch - relative)) > 1:
        return empty
    try:
        start = datetime.fromtimestamp(explicit if type(explicit) is int else epoch - relative, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return empty
    return {'relative_time_seconds': relative, 'session_start_time': start}


def _sort_key(row):
    sid = row.platform_submission_id
    return row.creation_time, int(sid) if sid.isdigit() else 0, sid


def participation_start(participation, rows):
    start = getattr(participation, 'session_start_time', None)
    if start:
        return start
    if not participation.is_virtual:
        return participation.contest.start_time
    duration = participation.contest.duration_seconds
    if not duration:
        return None
    candidates = {s.session_start_time for s in rows
                  if s.participant_type == 'VIRTUAL' and s.session_start_time}
    date = participation.participation_date
    if date:
        candidates = {start for start in candidates if start <= date < start + timedelta(seconds=duration)}
    return next(iter(candidates)) if len(candidates) == 1 else None


def in_participation_window(start, duration, creation_time, session_start_time=None, relative_time_seconds=None):
    """The provider's relative clock handles fractional-second session starts."""
    if session_start_time == start and type(relative_time_seconds) is int:
        return 0 <= relative_time_seconds < duration
    return start <= creation_time < start + timedelta(seconds=duration)


def build_contest_results(participation, problem_ids, submissions, statuses=None):
    statuses = statuses or {}
    rows = sorted({s.platform_submission_id: s for s in submissions
                   if s.user_id == participation.user_id}.values(), key=_sort_key)
    imported_acs = {s.problem_id for s in rows if s.verdict == 'OK'}
    start = participation_start(participation, rows)
    duration = participation.contest.duration_seconds
    end = start + timedelta(seconds=duration) if start and duration and duration > 0 else None
    kind = 'VIRTUAL' if participation.is_virtual else 'CONTESTANT'
    complete = bool(getattr(participation, 'results_synced_at', None) and start and end)
    during = {}
    practice_acs = {}
    for row in rows:
        if end and row.participant_type == 'PRACTICE' and row.verdict == 'OK' and row.creation_time >= end:
            practice_acs.setdefault(row.problem_id, row.creation_time)
        if not start or not end or row.participant_type != kind or not in_participation_window(
                start, duration, row.creation_time, row.session_start_time, row.relative_time_seconds):
            continue
        if participation.is_virtual and row.session_start_time is None:
            # A matching wall-clock window cannot identify an old virtual session.
            complete = False
            continue
        if row.session_start_time and row.session_start_time != start:
            continue
        during.setdefault(row.problem_id, []).append(row)

    results = {}
    for pid in problem_ids:
        attempts = during.get(pid, [])
        first_ac = next((s for s in attempts if s.verdict == 'OK'), None)
        before, after = Counter(), Counter()
        for row in attempts:
            label = ERROR_VERDICTS.get(row.verdict)
            if label:
                target = after if first_ac and _sort_key(row) > _sort_key(first_ac) else before
                target[label] += 1
        accepted = bool(first_ac) if start and end else (True if statuses.get(pid) == 'SOLVED_LIVE' else None)
        post_ac = practice_acs.get(pid)
        upsolved = not accepted and (statuses.get(pid) == 'UPSOLVED' or bool(post_ac))
        results[pid] = {
            'accepted': accepted,
            'failed_attempts': sum(before.values()) if complete else None,
            'first_ac_seconds': (first_ac.relative_time_seconds if first_ac.session_start_time == start
                                 and first_ac.relative_time_seconds is not None
                                 else int((first_ac.creation_time - start).total_seconds())) if first_ac else None,
            'errors_before_ac': dict(before), 'errors_after_ac': dict(after),
            'compilation_errors': sum(s.verdict == 'COMPILATION_ERROR' for s in attempts),
            'coverage': 'complete' if complete else 'partial',
            'is_upsolved': bool(upsolved), 'upsolved_at': post_ac if upsolved else None,
            'manual_completion': bool(upsolved and pid not in imported_acs),
        }
    return results


def contest_results(participation, problems):
    """One bounded query; no HTTP, writes, or per-problem queries."""
    from api.models import Submission
    rows = list(Submission.objects.filter(user_id=participation.user_id,
                                         problem__contest_id=participation.contest_id))
    statuses = {p.id: p._tracking.system_status for p in problems if getattr(p, '_tracking', None)}
    return build_contest_results(participation, [p.id for p in problems], rows, statuses)


def confirmed_progress(user, participations, statuses):
    """Batch projection for cards/charts; legacy partial histories keep tracking totals."""
    from api.models import Problem, Submission
    confirmed = [p for p in participations if p.results_synced_at
                 and participation_start(p, []) and (p.contest.duration_seconds or 0) > 0]
    if not confirmed:
        return {}
    contest_ids = [p.contest_id for p in confirmed]
    catalogue = dict(Problem.objects.filter(contest_id__in=contest_ids).values_list('id', 'contest_id'))
    problems_by_contest = {cid: [] for cid in contest_ids}
    rows_by_contest = {cid: [] for cid in contest_ids}
    for pid, cid in catalogue.items():
        problems_by_contest[cid].append(pid)
    for row in Submission.objects.filter(user=user, problem__contest_id__in=contest_ids):
        rows_by_contest[catalogue[row.problem_id]].append(row)

    counts = {}
    for part in confirmed:
        results = build_contest_results(part, problems_by_contest[part.contest_id],
                                        rows_by_contest[part.contest_id], statuses)
        if any(r['coverage'] != 'complete' for r in results.values()):
            continue
        progress = dict(solved_live=0, pending_upsolve=0, upsolved=0, unattempted=0, total=len(results))
        for pid, result in results.items():
            if result['accepted']:
                key = 'solved_live'
            elif result['is_upsolved']:
                key = 'upsolved'
            elif result['failed_attempts'] or statuses.get(pid) == 'PENDING_UPSOLVE':
                key = 'pending_upsolve'
            else:
                key = 'unattempted'
            progress[key] += 1
        counts[part.contest_id] = progress
    return counts
