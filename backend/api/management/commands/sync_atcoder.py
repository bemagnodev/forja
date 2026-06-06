import time
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from api.models import User, Problem, Submission, UserProblemTracking, PlatformChoices, ContestParticipation
from api.services.atcoder_client import AtCoderClient

class Command(BaseCommand):
    help = 'Sincroniza as submissões do AtCoder buscando na The Kenkoooo API.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--handle',
            type=str,
            help='Especifica um único atcoder_handle para focar no sync.'
        )
        parser.add_argument(
            '--force-full',
            action='store_true',
            help='Ignora a data do último sincronismo e puxa tudo de novo (Full Sync).'
        )

    def handle(self, *args, **kwargs):
        handle_arg = kwargs.get('handle')
        force_full = kwargs.get('force_full')

        if handle_arg:
            users = User.objects.filter(atcoder_handle=handle_arg)
        else:
            users = User.objects.exclude(atcoder_handle__isnull=True).exclude(atcoder_handle__exact='')

        if not users.exists():
            self.stdout.write(self.style.WARNING("Nenhum usuário apto com atcoder_handle encontrado para a sincronização."))
            return

        client = AtCoderClient()

        # Carrega mapa de títulos uma vez antes do loop (O(1) lookup por problema)
        self.stdout.write("  > Carregando mapa de títulos da API Kenkoooo...")
        problems_data = client.get_problems()
        title_map = {p['id']: p['title'] for p in problems_data if 'id' in p and 'title' in p}
        self.stdout.write(f"  > {len(title_map)} títulos carregados.")

        for user in users:
            self.stdout.write(self.style.MIGRATE_HEADING(f"[{user.username}] Buscando submissoes usando a Kenkoooo API para {user.atcoder_handle}..."))
            
            # Sincronismo Incremental Senior
            from_epoch = 0
            if not force_full and user.atcoder_last_sync_time:
                from_epoch = user.atcoder_last_sync_time
                self.stdout.write(f"  > Incremental ativo: Buscando apenas a partir do Epoch {from_epoch}")
            else:
                self.stdout.write("  > Full Sync ativado: Buscando todo o historico (Epoch 0)")

            submissions = client.get_user_submissions(user.atcoder_handle, from_epoch=from_epoch)
            
            self.stdout.write(f"  > Recebido: {len(submissions)} submissoes na payload. Persistindo via Dual-State FSM...")
            
            inserts = 0
            max_epoch = from_epoch

            for sub_data in submissions:
                platform_id = sub_data['problem_id']
                sub_id = str(sub_data['id'])
                verdict = sub_data['result']
                epoch_sec = sub_data['epoch_second']
                
                if verdict in ['WJ', 'WR']:
                    continue
                
                if not force_full and user.atcoder_last_sync_time and epoch_sec <= user.atcoder_last_sync_time:
                    continue
                
                
                # 1. Model: Problem — usa título real da API se disponível
                real_title = title_map.get(platform_id, platform_id)
                problem, _ = Problem.objects.get_or_create(
                    platform=PlatformChoices.ATCODER,
                    platform_id=platform_id,
                    defaults={
                        'title': real_title,
                        'contest': None
                    }
                )
                # Se o título ainda é fallback (title == platform_id), atualiza agora
                if problem.title == problem.platform_id and real_title != platform_id:
                    problem.title = real_title
                    problem.save(update_fields=['title'])

                # 2. Model: Submission
                creation_dt = datetime.fromtimestamp(epoch_sec, tz=timezone.UTC)
                
                # Analisar Janela do Contest (Live vs Practice)
                p_type = Submission.ParticipantType.PRACTICE
                if problem.contest and problem.contest.start_time and problem.contest.duration_seconds:
                    c_start = problem.contest.start_time
                    c_end = c_start + timezone.timedelta(seconds=problem.contest.duration_seconds)
                    if c_start <= creation_dt <= c_end:
                        p_type = Submission.ParticipantType.CONTESTANT

                submission, _ = Submission.objects.update_or_create(
                    platform_submission_id=sub_id,
                    defaults={
                        'problem': problem,
                        'user': user,
                        'participant_type': p_type,
                        'verdict': verdict,
                        'creation_time': creation_dt
                    }
                )

                # 3. Model: UserProblemTracking (O coração)
                tracking, _ = UserProblemTracking.objects.get_or_create(
                    user=user, 
                    problem=problem
                )
                
                # O status de sistema mapeia condicionalmente pela janela de tempo
                is_contest_effort = p_type in [Submission.ParticipantType.CONTESTANT, Submission.ParticipantType.VIRTUAL]
                
                # Efeito Propagação de Contest
                if is_contest_effort and problem.contest:
                    participation, created = ContestParticipation.objects.get_or_create(
                        user=user, 
                        contest=problem.contest,
                        defaults={'participation_date': creation_dt}
                    )
                    if created:
                        # Espalha Unattempted para todas as outras questões do Contest
                        all_problems_in_contest = Problem.objects.filter(contest=problem.contest)
                        for p_in_contest in all_problems_in_contest:
                            UserProblemTracking.objects.get_or_create(
                                user=user, 
                                problem=p_in_contest,
                                defaults={'system_status': UserProblemTracking.SystemStatus.UNATTEMPTED, 'review_status': UserProblemTracking.ReviewStatus.PENDING_TRIAGE}
                            )

                has_participation = problem.contest and ContestParticipation.objects.filter(user=user, contest=problem.contest).exists()

                if verdict == 'AC':
                    if is_contest_effort:
                        new_sys_status = UserProblemTracking.SystemStatus.SOLVED_LIVE
                    elif has_participation:
                        new_sys_status = UserProblemTracking.SystemStatus.UPSOLVED
                    else:
                        new_sys_status = UserProblemTracking.SystemStatus.PRACTICE_AC
                else:
                    if is_contest_effort:
                        new_sys_status = UserProblemTracking.SystemStatus.PENDING_UPSOLVE
                    elif has_participation:
                        new_sys_status = UserProblemTracking.SystemStatus.PENDING_UPSOLVE
                    else:
                        new_sys_status = UserProblemTracking.SystemStatus.PRACTICE_WA
                
                # É OBRIGATÓRIO SALVAR INDIVIDUALMENTE e não via bulk_update
                # Porque o nosso override de self._sync_system_to_review(old_instance) roda no momento de save()
                if tracking.system_status != new_sys_status:
                    tracking.system_status = new_sys_status
                    tracking.save()
                    inserts += 1
                
                if epoch_sec > max_epoch:
                    max_epoch = epoch_sec

            # Garantia de Integridade (Atomicidade Manual)
            if max_epoch > 0:
                user.atcoder_last_sync_time = max_epoch
                user.save()

            self.stdout.write(self.style.SUCCESS(f"Finalizado para {user.username}! Status modificados: {inserts}"))
