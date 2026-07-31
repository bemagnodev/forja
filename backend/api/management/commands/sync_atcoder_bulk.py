"""
Comando: sync_atcoder_bulk

Versao otimizada do sync_atcoder usando bulk_create para ambientes
com alta latencia de banco (ex: Supabase free tier).

Diferenca da versao original:
- Coleta TODAS as submissoes da API Kenkoooo de uma vez (ja era assim)
- Prepara todos os objetos em memoria (listas Python) sem tocar no banco
- Persiste tudo de uma vez via bulk_create em chunks de 500
  (1 query SQL por 500 registros, vs 1 query por registro antes)

Uso:
    python manage.py sync_atcoder_bulk --handle tourist
    python manage.py sync_atcoder_bulk  (roda para todos com atcoder_handle)
    python manage.py sync_atcoder_bulk --handle tourist --force-full
"""
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from api.models import (
    User, Problem, Submission, UserProblemTracking,
    PlatformChoices, ContestParticipation
)
from api.services.atcoder_client import AtCoderClient

CHUNK_SIZE = 500


def bulk_upsert(model, objects, stdout):
    """Insere em chunks ignorando conflitos (idempotente)."""
    total = len(objects)
    for i in range(0, total, CHUNK_SIZE):
        chunk = objects[i: i + CHUNK_SIZE]
        model.objects.bulk_create(chunk, ignore_conflicts=True)
        stdout.write(f'    {min(i + CHUNK_SIZE, total)}/{total}...')


class Command(BaseCommand):
    help = 'Sincroniza submissoes do AtCoder via Kenkoooo API usando bulk_create.'

    def add_arguments(self, parser):
        parser.add_argument('--handle', type=str, help='Especifica um atcoder_handle.')
        parser.add_argument('--force-full', action='store_true', help='Ignora watermark e faz full sync.')

    def handle(self, *args, **kwargs):
        handle_arg = kwargs.get('handle')
        force_full = kwargs.get('force_full')

        if handle_arg:
            users = User.objects.filter(atcoder_handle=handle_arg)
        else:
            users = User.objects.exclude(atcoder_handle__isnull=True).exclude(atcoder_handle__exact='')

        if not users.exists():
            self.stdout.write(self.style.WARNING('Nenhum usuario com atcoder_handle encontrado.'))
            return

        client = AtCoderClient()

        # Carrega mapa de titulos uma vez (O(1) lookup)
        self.stdout.write('> Carregando mapa de titulos da API Kenkoooo...')
        problems_data = client.get_problems()
        title_map = {p['id']: p['title'] for p in problems_data if 'id' in p and 'title' in p}
        self.stdout.write(f'> {len(title_map)} titulos carregados.')

        for user in users:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'[{user.username}] AtCoder handle: {user.atcoder_handle}'
            ))

            from_epoch = 0
            if not force_full and user.atcoder_last_sync_time:
                from_epoch = user.atcoder_last_sync_time
                self.stdout.write(f'> Incremental a partir do Epoch {from_epoch}')
            else:
                self.stdout.write('> Full Sync (Epoch 0)')

            # 1. Busca todas as submissoes da API (1 request HTTP)
            submissions = client.get_user_submissions(user.atcoder_handle, from_epoch=from_epoch)
            self.stdout.write(f'> {len(submissions)} submissoes recebidas da API.')

            if not submissions:
                self.stdout.write(self.style.WARNING('Nenhuma submissao nova. Pulando.'))
                continue

            # Filtra submissoes invalidas/ja sincronizadas
            valid_subs = [
                s for s in submissions
                if s.get('result') not in ['WJ', 'WR']
                and (force_full or not user.atcoder_last_sync_time or s['epoch_second'] > user.atcoder_last_sync_time)
            ]
            self.stdout.write(f'> {len(valid_subs)} submissoes validas para processar.')

            # 2. Coleta IDs de Problems/Submissions/Trackings ja existentes (1 query cada)
            self.stdout.write('> Pre-carregando estado atual do banco...')
            existing_problem_ids = set(
                Problem.objects.filter(platform=PlatformChoices.ATCODER)
                .values_list('platform_id', flat=True)
            )
            existing_sub_ids = set(
                Submission.objects.filter(user=user, problem__platform=PlatformChoices.ATCODER)
                .values_list('platform_submission_id', flat=True)
            )
            existing_tracking_ids = set(
                UserProblemTracking.objects.filter(user=user, problem__platform=PlatformChoices.ATCODER)
                .values_list('problem__platform_id', flat=True)
            )

            # 3. Prepara Problems novos em memoria
            new_problem_ids = set()
            new_problems = []
            for sub in valid_subs:
                pid = sub['problem_id']
                if pid not in existing_problem_ids and pid not in new_problem_ids:
                    new_problems.append(Problem(
                        platform=PlatformChoices.ATCODER,
                        platform_id=pid,
                        title=title_map.get(pid, pid),
                        contest=None,
                    ))
                    new_problem_ids.add(pid)

            # 3a. Persiste Problems novos (necessario antes das Submissions que referenciam)
            if new_problems:
                self.stdout.write(f'> Inserindo {len(new_problems)} novos problemas...')
                bulk_upsert(Problem, new_problems, self.stdout)
                existing_problem_ids.update(new_problem_ids)

            # Recarrega mapa de Problem objects para FK lookup
            # (apenas os problemas AtCoder relevantes para este usuario)
            platform_id_to_problem = {
                p.platform_id: p
                for p in Problem.objects.filter(
                    platform=PlatformChoices.ATCODER,
                    platform_id__in={s['problem_id'] for s in valid_subs}
                )
            }

            # 4. Prepara Submissions e Trackings em memoria
            new_subs = []
            new_trackings = []
            max_epoch = from_epoch

            # Hierarquia de prioridade da FSM (protege contra downgrade)
            status_priority = {
                UserProblemTracking.SystemStatus.SOLVED_LIVE: 60,
                UserProblemTracking.SystemStatus.UPSOLVED: 50,
                UserProblemTracking.SystemStatus.PRACTICE_AC: 40,
                UserProblemTracking.SystemStatus.PENDING_UPSOLVE: 30,
                UserProblemTracking.SystemStatus.PRACTICE_WA: 20,
                UserProblemTracking.SystemStatus.UNATTEMPTED: 10,
            }

            # Mapa de status atual dos trackings existentes (para aplicar hierarquia)
            existing_tracking_status = {
                t.problem.platform_id: t.system_status
                for t in UserProblemTracking.objects.filter(
                    user=user, problem__platform=PlatformChoices.ATCODER
                ).select_related('problem')
            } if existing_tracking_ids else {}

            # Acumula o melhor status por problema (para submissoes multiplas)
            best_status_per_problem = {}

            for sub in valid_subs:
                pid = sub['problem_id']
                sub_id = str(sub['id'])
                verdict = sub['result']
                epoch_sec = sub['epoch_second']

                if epoch_sec > max_epoch:
                    max_epoch = epoch_sec

                problem = platform_id_to_problem.get(pid)
                if not problem:
                    continue

                # Calcula participantType pela janela de tempo do contest
                p_type = Submission.ParticipantType.PRACTICE
                if problem.contest and problem.contest.start_time and problem.contest.duration_seconds:
                    c_start = problem.contest.start_time
                    c_end = c_start + timezone.timedelta(seconds=problem.contest.duration_seconds)
                    creation_dt = datetime.fromtimestamp(epoch_sec, tz=timezone.UTC)
                    if c_start <= creation_dt <= c_end:
                        p_type = Submission.ParticipantType.CONTESTANT

                # Prepara Submission
                if sub_id not in existing_sub_ids:
                    new_subs.append(Submission(
                        platform_submission_id=sub_id,
                        problem=problem,
                        user=user,
                        participant_type=p_type,
                        verdict=verdict,
                        creation_time=datetime.fromtimestamp(epoch_sec, tz=timezone.UTC),
                    ))
                    existing_sub_ids.add(sub_id)

                # Calcula status FSM
                is_contest = p_type == Submission.ParticipantType.CONTESTANT
                has_participation = ContestParticipation.objects.filter(
                    user=user, contest=problem.contest
                ).exists() if problem.contest else False

                if verdict == 'AC':
                    if is_contest:
                        new_status = UserProblemTracking.SystemStatus.SOLVED_LIVE
                    elif has_participation:
                        new_status = UserProblemTracking.SystemStatus.UPSOLVED
                    else:
                        new_status = UserProblemTracking.SystemStatus.PRACTICE_AC
                else:
                    if is_contest or has_participation:
                        new_status = UserProblemTracking.SystemStatus.PENDING_UPSOLVE
                    else:
                        new_status = UserProblemTracking.SystemStatus.PRACTICE_WA

                # Mantém apenas o melhor status por problema neste lote
                current_best = best_status_per_problem.get(pid)
                if current_best is None or status_priority[new_status] > status_priority[current_best]:
                    best_status_per_problem[pid] = new_status

            # 4a. Prepara Trackings: apenas problemas novos ou com upgrade de status
            for pid, new_status in best_status_per_problem.items():
                problem = platform_id_to_problem.get(pid)
                if not problem:
                    continue

                current_status = existing_tracking_status.get(pid)
                if current_status is None:
                    # Problema novo: cria tracking
                    # Calcula review_status baseado no system_status (logica da FSM)
                    if new_status in [
                        UserProblemTracking.SystemStatus.SOLVED_LIVE,
                        UserProblemTracking.SystemStatus.UPSOLVED,
                        UserProblemTracking.SystemStatus.PRACTICE_AC,
                    ]:
                        review_status = UserProblemTracking.ReviewStatus.DONE
                    elif new_status in [
                        UserProblemTracking.SystemStatus.PENDING_UPSOLVE,
                        UserProblemTracking.SystemStatus.PRACTICE_WA,
                    ]:
                        review_status = UserProblemTracking.ReviewStatus.DOABLE
                    else:
                        review_status = UserProblemTracking.ReviewStatus.PENDING_TRIAGE

                    new_trackings.append(UserProblemTracking(
                        user=user,
                        problem=problem,
                        system_status=new_status,
                        review_status=review_status,
                    ))

            # 5. Persiste tudo em bulk
            self.stdout.write(f'> Inserindo {len(new_subs)} submissoes em bulk...')
            if new_subs:
                bulk_upsert(Submission, new_subs, self.stdout)

            self.stdout.write(f'> Inserindo {len(new_trackings)} trackings em bulk...')
            if new_trackings:
                bulk_upsert(UserProblemTracking, new_trackings, self.stdout)

            # 6. Atualiza watermark somente se houve progresso
            if max_epoch > (from_epoch or 0):
                user.atcoder_last_sync_time = max_epoch
                user.save()
                self.stdout.write(f'> Watermark atualizado para Epoch {max_epoch}')

            self.stdout.write(self.style.SUCCESS(
                f'[OK] Concluido para {user.username}: '
                f'{len(new_subs)} subs + {len(new_trackings)} trackings'
            ))
