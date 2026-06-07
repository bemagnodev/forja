import time
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from api.models import User, Problem, Submission, UserProblemTracking, PlatformChoices, ContestParticipation, Contest
from api.services.codeforces_client import CodeforcesClient

class Command(BaseCommand):
    help = 'Sincroniza as submissões vitais do Codeforces, abastecendo o Tracking via motor FSM Dual-State.'

    def add_arguments(self, parser):
        parser.add_argument('--handle', type=str, help='Especifica um único cf_handle.')
        parser.add_argument('--force-full', action='store_true', help='Ignora a data do último sincronismo e puxa tudo (Full Sync).')

    def handle(self, *args, **kwargs):
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

        for user in users:
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

            while not is_synced:
                submissions = client.get_user_submissions(user.cf_handle, from_idx=from_idx, count=count)
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
                    
                if epoch_sec > max_epoch:
                    max_epoch = epoch_sec
            
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

                # Fetch DINÂMICO de Gyms e suas Questões
                if is_gym:
                    c_exists = Contest.objects.filter(platform_id=contest_id).exists()
                    if not c_exists:
                        self.stdout.write(f"    > Contest Gym {contest_id} não encontrado. Buscando dados completos...")
                        gym_data = client.get_gym_standings(contest_id)
                        if gym_data:
                            c_meta = gym_data.get('contest', {})
                            c_start = None
                            if c_meta.get('startTimeSeconds'):
                                c_start = datetime.fromtimestamp(c_meta.get('startTimeSeconds'), tz=timezone.UTC)
                                
                            c_obj, _ = Contest.objects.update_or_create(
                                platform=PlatformChoices.CF_GYM,
                                platform_id=contest_id,
                                defaults={
                                    'name': c_meta.get('name', f"Gym {contest_id}"),
                                    'start_time': c_start,
                                    'duration_seconds': c_meta.get('durationSeconds', 0)
                                }
                            )
                            
                            for p_meta in gym_data.get('problems', []):
                                p_id = f"{contest_id}{p_meta.get('index', '')}"
                                p_name = p_meta.get('name', '')
                                p_title = f"{p_meta.get('index', '')}. {p_name}" if p_name else p_id
                                
                                Problem.objects.update_or_create(
                                    platform=PlatformChoices.CF_GYM,
                                    platform_id=p_id,
                                    defaults={
                                        'title': p_title,
                                        'contest': c_obj,
                                        'platform_metadata': {
                                            'rating': p_meta.get('rating'),
                                            'tags': p_meta.get('tags', [])
                                        }
                                    }
                                )

                cont_obj = Contest.objects.filter(platform_id=contest_id).first()

                # 1. Problem 
                problem, _ = Problem.objects.get_or_create(
                    platform=platform_type,
                    platform_id=platform_id,
                    defaults={
                        'title': title,
                        'contest': cont_obj,
                        'platform_metadata': {
                            'rating': prob_data.get('rating'),
                            'tags': prob_data.get('tags', [])
                        }
                    }
                )

                # 2. Submission (Data Absoluta)
                creation_dt = datetime.fromtimestamp(epoch_sec, tz=timezone.UTC)
                
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
                        'creation_time': creation_dt
                    }
                )

                # Efeito Propagação: Criar Participation Shield e engatilhar Tracking Unattempted no Contest inteiro!
                is_contest_effort = p_type in [Submission.ParticipantType.CONTESTANT, Submission.ParticipantType.VIRTUAL]
                
                if is_contest_effort and problem.contest:
                    is_virtual_participation = p_type == Submission.ParticipantType.VIRTUAL
                    participation = ContestParticipation.objects.filter(
                        user=user, 
                        contest=problem.contest
                    ).first()
                    created = False
                    if not participation:
                        participation = ContestParticipation.objects.create(
                            user=user,
                            contest=problem.contest,
                            participation_date=creation_dt,
                            is_virtual=is_virtual_participation
                        )
                        created = True
                    if created:
                        # Espalha Unattempted para todas as outras questões do Contest
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

            # Garantia Atômica Manual do Watermark 
            if max_epoch > 0:
                user.cf_last_sync_time = max_epoch
                user.save()

            self.stdout.write(self.style.SUCCESS(f"Finalizado {user.username}! ({inserts} alterações mapeadas no CF)"))
