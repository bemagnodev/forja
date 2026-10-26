import time
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
from api.models import User, Problem, Submission, UserProblemTracking, PlatformChoices, ContestParticipation, Contest
from api.services.codeforces_client import CodeforcesClient
from api.services.codeforces_gym_service import ensure_codeforces_gym_metadata
from api.services.problem_metadata import upsert_problem_metadata
from api.services.cf_sync_runtime import exclusive_cf_sync
from api.services.contest_results import cf_submission_timing

class Command(BaseCommand):
    help = 'Sincroniza as submissões vitais do Codeforces, abastecendo o Tracking via motor FSM Dual-State.'

    def add_arguments(self, parser):
        parser.add_argument('--handle', type=str, help='Especifica um único cf_handle.')
        parser.add_argument('--force-full', action='store_true', help='Ignora a data do último sincronismo e puxa tudo (Full Sync).')

    def handle(self, *args, **kwargs):
        with exclusive_cf_sync():
            return self._sync(*args, **kwargs)

    def _sync(self, *args, **kwargs):
        handle_arg = kwargs.get('handle')
        force_full = kwargs.get('force_full')

        if handle_arg:
            users = User.objects.filter(cf_handle=handle_arg)
        else:
            users = User.objects.exclude(cf_handle__isnull=True).exclude(cf_handle__exact='')

        if not users.exists():
            self.stdout.write(self.style.WARNING("Nenhum usuário apto com cf_handle encontrado."))
            return

        client = CodeforcesClient()
        incomplete = False

        for user in users:
            previous_checkpoint = None if force_full else user.cf_last_sync_time
            self.stdout.write(self.style.MIGRATE_HEADING(f"[{user.username}] Baixando Timeline do CF para {user.cf_handle}..."))
            if not force_full and user.cf_last_sync_time:
                self.stdout.write(f"  > Incremental ativo: Wall configurada p/ Epoch {user.cf_last_sync_time}")
            else:
                self.stdout.write("  > Full Sync ativado: Lendo o histórico do topo ao fim")
            
            inserts = 0
            max_epoch = 0
            from_idx = 1
            count = 500
            is_synced = False
            
            all_sub_data = []
            attempted_gyms = set()
            synced_gyms = set()
            unavailable_gyms = set()
            transient_failed_gyms = set()
            had_failures = False

            while not is_synced:
                result = client.get_user_submissions_result(user.cf_handle, from_idx=from_idx, count=count)
                if not result.is_success:
                    raise CommandError("Falha ao obter histórico do Codeforces. Progresso preservado; tente novamente mais tarde.")
                submissions = result.data
                if not submissions:
                    break
                    
                self.stdout.write(f"  > Lendo {len(submissions)} submissões (a partir do índice {from_idx})...")
                
                for sub_data in submissions:
                    epoch_sec = sub_data.get('creationTimeSeconds')
                    if not epoch_sec: continue
                    
                    if not force_full and user.cf_last_sync_time and epoch_sec <= user.cf_last_sync_time:
                        self.stdout.write("  > Sincronismo Incremental concluído! Submissões antigas ignoradas.")
                        is_synced = True
                        break
                        
                    all_sub_data.append(sub_data)
                
                if is_synced:
                    break
                from_idx += count

            self.stdout.write(f"  > Processando {len(all_sub_data)} submissões em Ordem Cronológica (Memória Reversa)...")
            
            for sub_data in reversed(all_sub_data):
                sub_id = str(sub_data['id'])
                verdict = sub_data.get('verdict', 'UNKNOWN')
                epoch_sec = sub_data.get('creationTimeSeconds')
                
                if verdict == 'TESTING':
                    continue
                    
                prob_data = sub_data.get('problem', {})
                contest_id_num = prob_data.get('contestId')
                index = prob_data.get('index', '')
                if not contest_id_num: continue
                
                contest_id = str(contest_id_num)
                platform_id = f"{contest_id}{index}"
                name = prob_data.get('name', '')
                title = f"{index}. {name}" if name else platform_id

                is_gym = int(contest_id) >= 100000
                platform_type = PlatformChoices.CF_GYM if is_gym else PlatformChoices.CF_OFFICIAL

                # Sincronização e garantia de metadados de Gyms e catálogo completo de problemas
                if is_gym:
                    if contest_id not in attempted_gyms:
                        attempted_gyms.add(contest_id)
                        self.stdout.write(f"    > Assegurando metadados e problemas do Gym {contest_id}...")
                        gym_res = ensure_codeforces_gym_metadata(contest_id, client=client)
                        if gym_res.is_success:
                            synced_gyms.add(contest_id)
                        elif gym_res.is_permanent_failure:
                            unavailable_gyms.add(contest_id)
                        elif gym_res.is_transient_failure:
                            transient_failed_gyms.add(contest_id)

                    # Toda falha de catálogo retém o checkpoint; sem dados locais, adia a submissão.
                    if contest_id in transient_failed_gyms:
                        had_failures = True
                        local_contest = Contest.objects.filter(platform=PlatformChoices.CF_GYM, platform_id=contest_id).first()
                        has_local_data = local_contest and local_contest.problems.exists()
                        if not has_local_data:
                            self.stdout.write(self.style.WARNING(f"    [!] Falha transitória ao obter metadados do Gym {contest_id}. Submissão {sub_id} adiada para o próximo sync."))
                            had_failures = True
                            continue

                    # Se for permanentemente indisponível/privado, aplica fallback provisório para não travar o sync
                    if contest_id in unavailable_gyms:
                        cont_obj = Contest.objects.filter(platform=PlatformChoices.CF_GYM, platform_id=contest_id).first()
                        if not cont_obj:
                            cont_obj = Contest.objects.create(
                                platform=PlatformChoices.CF_GYM,
                                platform_id=contest_id,
                                name=f"Gym {contest_id}",
                                duration_seconds=0
                            )

                cont_obj = Contest.objects.filter(platform=platform_type, platform_id=contest_id).first()

                # 1. Problem - Preserva metadados existentes (rating/tags do catálogo e IA) se a submissão vier sem eles
                problem, _ = upsert_problem_metadata(
                    platform=platform_type,
                    platform_id=platform_id,
                    fields={
                        'title': title,
                        'contest': cont_obj,
                    },
                    metadata={'rating': prob_data.get('rating'), 'tags': prob_data.get('tags', [])},
                )

                # 2. Submission (Data Absoluta)
                creation_dt = datetime.fromtimestamp(epoch_sec, tz=timezone.UTC)
                timing = cf_submission_timing(sub_data)
                
                p_type = Submission.ParticipantType.PRACTICE
                cf_participant = sub_data.get('author', {}).get('participantType')
                
                if cf_participant == 'CONTESTANT':
                    p_type = Submission.ParticipantType.CONTESTANT
                elif cf_participant == 'VIRTUAL':
                    p_type = Submission.ParticipantType.VIRTUAL
                elif problem.contest and problem.contest.start_time and problem.contest.duration_seconds:
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
                        'creation_time': creation_dt,
                        **{key: value for key, value in timing.items() if value is not None},
                    }
                )

                # Efeito Propagação: Criar Participation Shield e engatilhar Tracking Unattempted no Contest inteiro!
                is_contest_effort = p_type in [Submission.ParticipantType.CONTESTANT, Submission.ParticipantType.VIRTUAL]
                
                if is_contest_effort and problem.contest:
                    is_virtual_participation = p_type == Submission.ParticipantType.VIRTUAL
                    participation, _ = ContestParticipation.objects.get_or_create(
                        user=user, 
                        contest=problem.contest,
                        defaults={
                            'participation_date': creation_dt,
                            'is_virtual': is_virtual_participation
                        }
                    )
                    if participation.session_start_time is None and timing['session_start_time']:
                        participation.session_start_time = timing['session_start_time']
                        participation.save(update_fields=['session_start_time'])
                    # Garante Tracking UNATTEMPTED para todas as questões do Contest
                    all_problems_in_contest = Problem.objects.filter(contest=problem.contest)
                    for p_in_contest in all_problems_in_contest:
                        UserProblemTracking.objects.get_or_create(
                            user=user,
                            problem=p_in_contest,
                            defaults={'system_status': UserProblemTracking.SystemStatus.UNATTEMPTED, 'review_status': UserProblemTracking.ReviewStatus.PENDING_TRIAGE}
                        )

                # 3. UserProblemTracking (Máquina de Estado com Defesa Upsolve)
                tracking, _ = UserProblemTracking.objects.get_or_create(
                    user=user, 
                    problem=problem
                )
                
                has_participation = problem.contest and ContestParticipation.objects.filter(user=user, contest=problem.contest).exists()
                
                if verdict == 'OK':
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
                
                # Hierarquia de estados para evitar downgrade (ex: UPSOLVED não pode sobrescrever SOLVED_LIVE)
                status_priority = {
                    UserProblemTracking.SystemStatus.SOLVED_LIVE: 60,
                    UserProblemTracking.SystemStatus.UPSOLVED: 50,
                    UserProblemTracking.SystemStatus.PRACTICE_AC: 40,
                    UserProblemTracking.SystemStatus.PENDING_UPSOLVE: 30,
                    UserProblemTracking.SystemStatus.PRACTICE_WA: 20,
                    UserProblemTracking.SystemStatus.UNATTEMPTED: 10,
                }
                
                current_prio = status_priority.get(tracking.system_status, 0)
                new_prio = status_priority.get(new_sys_status, 0)

                if new_prio > current_prio:
                    tracking.system_status = new_sys_status
                    tracking.save()
                    inserts += 1

                # Atualiza watermark somente após o processamento com sucesso da submissão
                if epoch_sec > max_epoch:
                    max_epoch = epoch_sec

            # Retenção do Watermark: somente avança se todas as submissões necessárias do lote foram processadas sem falha.
            # Nota: sem transação de banco em volta de todo o lote, o watermark não avança para prevenir perda de reprocessamento.
            if max_epoch > 0 and not had_failures:
                covered = ContestParticipation.objects.filter(user=user,
                    contest__platform__in=[PlatformChoices.CF_OFFICIAL, PlatformChoices.CF_GYM],
                    session_start_time__isnull=False)
                if previous_checkpoint:
                    covered = covered.filter(session_start_time__gte=datetime.fromtimestamp(previous_checkpoint, tz=timezone.UTC))
                covered.update(results_synced_at=timezone.now())
                user.cf_last_sync_time = max_epoch
                user.save()
            elif had_failures:
                incomplete = True
                self.stdout.write(self.style.WARNING(f"  [!] Watermark retido em {user.cf_last_sync_time} para {user.username} devido a falhas durante a sincronização."))

            self.stdout.write(self.style.SUCCESS(f"Finalizado {user.username}! ({inserts} alterações mapeadas no CF)"))
        if incomplete:
            return "incomplete"
