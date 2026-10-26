"""Explicit historical enrichment: never replays tracking or advances the sync cursor."""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from api.models import ContestParticipation, Submission, User
from api.services.codeforces_client import CodeforcesClient
from api.services.contest_results import cf_submission_timing, participation_start
from api.services.cf_sync_runtime import exclusive_cf_sync


class Command(BaseCommand):
    help = 'Prévia de metadados de uma participação CF. Use --apply para salvar apenas tempos e placar.'

    def add_arguments(self, parser):
        parser.add_argument('--handle', required=True)
        parser.add_argument('--contest-id', required=True, type=int)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        with exclusive_cf_sync():
            return self._hydrate(options)

    def _hydrate(self, options):
        try:
            user = User.objects.get(cf_handle=options['handle'])
            part = ContestParticipation.objects.select_related('contest').get(user=user,
                contest__platform__in=['CF_GYM', 'CF_OFFICIAL'], contest__platform_id=str(options['contest_id']))
        except (User.DoesNotExist, ContestParticipation.DoesNotExist, User.MultipleObjectsReturned):
            raise CommandError('Informe um handle único e um contest com participação já importada.') from None

        client = CodeforcesClient()
        existing = {s.platform_submission_id: s for s in Submission.objects.filter(user=user, problem__contest=part.contest)}
        timing = {}
        source_rows = {}
        offset = 1
        # Before the first effort minus duration, all records of this session have been traversed.
        cutoff = part.participation_date - timedelta(seconds=part.contest.duration_seconds or 0) if part.participation_date else None
        while True:
            response = client.get_user_submissions_result(user.cf_handle, from_idx=offset, count=500)
            if not response.is_success:
                raise CommandError('Histórico incompleto; nenhum metadado foi salvo. Tente novamente.')
            batch = response.data
            if not batch:
                break
            for raw in batch:
                sid = str(raw.get('id'))
                if str(raw.get('problem', {}).get('contestId')) == str(options['contest_id']):
                    source_rows[sid] = raw
                    if sid in existing:
                        timing[sid] = cf_submission_timing(raw)
            oldest = batch[-1].get('creationTimeSeconds')
            if cutoff and isinstance(oldest, int) and oldest < cutoff.timestamp():
                break
            offset += len(batch)

        for sid, values in timing.items():
            for key, value in values.items():
                setattr(existing[sid], key, value)
        start = participation_start(part, list(existing.values()))
        end = start + timedelta(seconds=part.contest.duration_seconds) if start and part.contest.duration_seconds else None
        kind = 'VIRTUAL' if part.is_virtual else 'CONTESTANT'
        relevant = {sid for sid, row in existing.items() if start and end
            and row.participant_type == kind and start <= row.creation_time < end
            and (row.session_start_time is None or row.session_start_time == start)}
        source_relevant = {sid for sid, raw in source_rows.items() if start and end
            and raw.get('author', {}).get('participantType') == kind
            and isinstance(raw.get('creationTimeSeconds'), int)
            and start.timestamp() <= raw['creationTimeSeconds'] < end.timestamp()
            and cf_submission_timing(raw)['session_start_time'] in [None, start]}
        complete = bool(start and end and relevant == source_relevant and all(
            cf_submission_timing(source_rows[sid])['session_start_time'] == start
            and source_rows[sid].get('verdict') == existing[sid].verdict for sid in source_relevant))
        self.stdout.write(f"{'Aplicação' if options['apply'] else 'Prévia'}: {len(timing)} submissões; "
                          f"cobertura {'completa' if complete and start else 'parcial'}. "
                          'Tracking e cursor de sincronização serão preservados.')
        if not options['apply']:
            return

        rank = self._ranking(client, part, user, start)
        with transaction.atomic():
            changed = [existing[sid] for sid in timing]
            if changed:
                Submission.objects.bulk_update(changed, ['relative_time_seconds', 'session_start_time'])
            if start:
                part.session_start_time = start
            part.results_synced_at = timezone.now() if complete and start else None
            fields = ['session_start_time', 'results_synced_at']
            if rank:
                part.rank, part.penalty, part.rank_context = rank
                fields += ['rank', 'penalty', 'rank_context']
            part.save(update_fields=fields)

    def _ranking(self, client, part, user, start):
        gym = part.contest.platform == 'CF_GYM'
        if part.is_virtual and (not gym or not start):
            return None
        params = {'contestId': part.contest.platform_id}
        if gym:
            params.update(handles=user.cf_handle, showUnofficial=True)
        response = client._make_request_result('contest.standings', params, authenticated=gym)
        if not response.is_success:
            self.stdout.write(self.style.WARNING('Placar indisponível; resultado anterior preservado.'))
            return None
        data = response.data or {}
        expected = 'VIRTUAL' if part.is_virtual else 'CONTESTANT'
        matches = []
        for row in data.get('rows', []):
            party = row.get('party', {})
            handles = [m.get('handle', '').casefold() for m in party.get('members', [])]
            if user.cf_handle.casefold() not in handles or party.get('participantType') != expected:
                continue
            if part.is_virtual and party.get('startTimeSeconds') != int(start.timestamp()):
                continue
            if type(row.get('rank')) is int and row['rank'] > 0:
                matches.append(row)
        if len(matches) != 1:
            return None
        row = matches[0]
        penalty = row.get('penalty') if data.get('contest', {}).get('type') == 'ICPC' else None
        if type(penalty) is not int or penalty < 0:
            penalty = None
        return row['rank'], penalty, 'VIRTUAL' if part.is_virtual else 'OFFICIAL'
