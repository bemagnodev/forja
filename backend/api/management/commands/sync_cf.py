import time
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from api.models import User, Problem, Submission, UserProblemTracking, PlatformChoices
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
            
            while not is_synced:
                submissions = client.get_user_submissions(user.cf_handle, from_idx=from_idx, count=count)
                if not submissions:
                    break
                    
                self.stdout.write(f"  > Lendo {len(submissions)} submissões (a partir do índice {from_idx})...")
                
                for sub_data in submissions:
                    sub_id = str(sub_data['id'])
                    verdict = sub_data.get('verdict', 'UNKNOWN')
                    epoch_sec = sub_data.get('creationTimeSeconds')
                    if not epoch_sec: continue
                    
                    if verdict == 'TESTING':
                        continue
                    
                    if not force_full and user.cf_last_sync_time and epoch_sec <= user.cf_last_sync_time:
                        self.stdout.write("  > Sincronismo Incremental concluído! Submissões antigas ignoradas.")
                        is_synced = True
                        break
                        
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

                # 1. Problem 
                problem, _ = Problem.objects.get_or_create(
                    platform=platform_type,
                    platform_id=platform_id,
                    defaults={
                        'title': title,
                        'contest': None,
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
                
                # Codeforces devolve exatamente quem era Contestant ou Virtual no ato!
                if cf_participant == 'CONTESTANT':
                    p_type = Submission.ParticipantType.CONTESTANT
                elif cf_participant == 'VIRTUAL':
                    p_type = Submission.ParticipantType.VIRTUAL
                elif problem.contest and problem.contest.start_time and problem.contest.duration_seconds:
                    # Trava secundária caso o CF falhe, cruzamos temporalmente igual no AtCoder
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

                # 3. UserProblemTracking (Máquina de Estado)
                tracking, _ = UserProblemTracking.objects.get_or_create(
                    user=user, 
                    problem=problem
                )
                
                # Rotear Sucesso ou Falha para Status de Sistema
                if verdict == 'OK':
                    if p_type == Submission.ParticipantType.CONTESTANT:
                        new_sys_status = UserProblemTracking.SystemStatus.SOLVED_LIVE
                    else:
                        new_sys_status = UserProblemTracking.SystemStatus.PRACTICE_AC
                else: # Inclui WRONG_ANSWER, TIME_LIMIT_EXCEEDED, MEMORY_LIMIT_EXCEEDED...
                    if p_type == Submission.ParticipantType.CONTESTANT:
                        new_sys_status = UserProblemTracking.SystemStatus.PENDING_UPSOLVE
                    else:
                        new_sys_status = UserProblemTracking.SystemStatus.PRACTICE_WA
                
                # Engatilhar salvamento 1-a-1 permitindo o self._sync_system_to_review rodar e blindar a FSM
                if tracking.system_status != new_sys_status:
                    tracking.system_status = new_sys_status
                    tracking.save()
                    inserts += 1
                
                if is_synced:
                    break
                from_idx += count

            # Garantia Atômica Manual do Watermark 
            if max_epoch > 0:
                user.cf_last_sync_time = max_epoch
                user.save()

            self.stdout.write(self.style.SUCCESS(f"Finalizado {user.username}! ({inserts} alterações mapeadas no CF)"))
