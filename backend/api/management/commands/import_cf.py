from django.core.management.base import BaseCommand
from api.models import Contest, Problem, Submission
import requests
import time
from datetime import datetime, timezone

class Command(BaseCommand):
    help = 'Importação inteligente do Codeforces com Detecção de Performance e Upsolving'

    def add_arguments(self, parser):
        parser.add_argument('--handle', type=str, help='Handle do usuário')
        parser.add_argument('--full', action='store_true', help='Ignora o break e sincroniza todo o histórico')
    
    def get_contest_name(self, contest_id):
        """
        Função auxiliar para buscar o nome real do contest.
        Chamada quando encontra um contest novo.
        """
        try:
            url = f"https://codeforces.com/api/contest.standings?contestId={contest_id}&from=1&count=1"
            res = requests.get(url, timeout=5).json()
            if res['status'] == 'OK':
                return res['result']['contest']['name']
        except Exception:
            pass
        return f"Contest {contest_id}" # Fallback se der erro
    
    def fetch_full_contest_problems(self, contest):
        """
        Povoa o banco com todos os problemas do contest (fantasmas).
        Garante que questões não tentadas apareçam no Dashboard.
        """
        if contest.has_full_problem_set:
            return
        
        try:
            url = f"https://codeforces.com/api/contest.standings?contestId={contest.external_id}&from=1&count=1"
            res = requests.get(url, timeout=10).json()
            if res['status'] == 'OK':
                for p_data in res['result']['problems']:
                    Problem.objects.get_or_create(
                        contest=contest,
                        index=p_data['index'],
                        defaults={
                            'name': p_data['name'],
                            'rating': p_data.get('rating'), 
                            'tags': p_data.get('tags', []),
                            'live_performance': Problem.LivePerformance.UNATTEMPTED,
                            'resolution_status': Problem.ResolutionStatus.PENDING
                        }
                    )
                contest.has_full_problem_set = True
                contest.save()
                self.stdout.write(self.style.SUCCESS(f"  [OK] Todos os problemas do contest {contest.external_id} foram mapeados."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [ERRO] Falha ao buscar problemas do contest {contest.external_id}: {e}"))

    def handle(self, *args, **options):
        handle = options['handle'] or 'bemagno'
        is_full_sync = options['full']
        self.stdout.write(self.style.WARNING(f"Iniciando ETL para: {handle} (Full Sync: {is_full_sync})..."))

        all_new_submissions = []
        start_index = 1
        batch_size = 100 # Pega de 100 em 100 
        keep_fetching = True

        while keep_fetching:
            self.stdout.write(f" Buscando submissões {start_index} até {start_index + batch_size}...")
            url = f"https://codeforces.com/api/user.status?handle={handle}&from={start_index}&count={batch_size}"
            
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"Erro HTTP: {response.status_code}"))
                    break

                data = response.json()
                if data['status'] != 'OK':
                    self.stdout.write(self.style.ERROR(f"Erro na API: {data.get('comment')}"))
                    break

                submissions = data['result']
                if not submissions:
                    self.stdout.write(self.style.SUCCESS("Fim do histórico encontrado."))
                    break

                # --- FILTRAGEM DE LOTE / ACÚMULO PARA FULL SYNC ---
                found_existing = False
                for sub in submissions:
                    sub_id = sub['id']
                    
                    # Se NÃO for full sync e a submissão já existe, achamos o ponto de parada
                    if not is_full_sync and Submission.objects.filter(submission_id=sub_id).exists():
                        self.stdout.write(self.style.SUCCESS(f"Submissão {sub_id} já existe. Parando busca incremental."))
                        found_existing = True 
                        break 
                    
                    # Se for full sync e já existe, apenas ignora e continua acumulando
                    if is_full_sync and Submission.objects.filter(submission_id=sub_id).exists():
                        continue
                        
                    all_new_submissions.append(sub)

                if found_existing:
                    keep_fetching = False
                    break # Sai do while loop

                # Avança para a próxima página
                start_index += batch_size
                time.sleep(1)  # Pausa para não bloquear a API

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao buscar API: {e}"))
                break

        # --- PROCESSAMENTO CRONOLÓGICO ---
        # Inverte a lista ACUMULADA para processar da mais ANTIGA para a mais NOVA
        if not all_new_submissions:
            self.stdout.write(self.style.SUCCESS("Nenhuma submissão nova para processar."))
            return

        all_new_submissions.reverse()
        self.stdout.write(self.style.SUCCESS(f"Processando {len(all_new_submissions)} submissões cronologicamente..."))


        for sub in all_new_submissions:
            try:
                sub_id = sub['id']

                # Aviso de Contest Fantasma
                if 'contestId' not in sub:
                    self.stdout.write(self.style.WARNING(f"Submissão {sub_id} ignorada (Sem contestId - Provável Gym/Mashup antigo)"))
                    continue

                # === Lógica de contests em grupo ===
                contest_id = sub['contestId']
                participant_type = sub['author']['participantType']
                is_after = (participant_type == 'PRACTICE') 

                # Verifica se foi em time (tem mais de 1 membro na lista author)
                members = sub.get('author', {}).get('members', [])
                is_team_submission = len(members) > 1

                contest, created_contest = Contest.objects.get_or_create(
                    external_id=contest_id,
                    defaults={
                        'name': f"Contest {contest_id}", # Placeholder inicial
                        'is_team': is_team_submission,
                        'platform': Contest.Platform.CODEFORCES
                    }
                )

                # Busca o nome real do contest na API e povoa problemas fantasmas
                if created_contest:
                    real_name = self.get_contest_name(contest_id)
                    contest.name = real_name
                    # Define se o contest foi pra valer ou apenas prática solta
                    if participant_type in ['CONTESTANT', 'VIRTUAL']:
                        contest.contest_type = 'LIVE' if participant_type == 'CONTESTANT' else 'VIRTUAL'
                    else:
                        contest.contest_type = 'PRACTICE'
                    contest.save()
                    self.stdout.write(f"  Contest novo cadastrado: {real_name}")
                    time.sleep(0.5) # Pausa para não bloquear a API 

                # Se foi participação real, cria todos os problemas como UNATTEMPTED
                if contest.contest_type in ['LIVE', 'VIRTUAL']:
                    self.fetch_full_contest_problems(contest)

                # === Lógica de problema ===
                prob_data = sub['problem']
                problem, prob_created = Problem.objects.get_or_create(
                    contest=contest,
                    index=prob_data['index'],
                    defaults={
                        'name': prob_data['name'],
                        'rating': prob_data.get('rating'),
                        'tags': prob_data.get('tags', []),
                        'live_performance': Problem.LivePerformance.NOT_PARTICIPATED 
                    }
                )

                # === Lógica de submissão ===
                dt = datetime.fromtimestamp(sub['creationTimeSeconds'], tz=timezone.utc)
                new_submission = Submission.objects.create(
                    problem=problem,
                    submission_id=sub_id,
                    verdict=sub.get('verdict', 'FAILED'),
                    creation_time=dt,
                    is_after_contest=is_after
                )
                
                # Ativa máquina de estados
                problem.update_state_from_submission(is_after, is_team_submission, new_submission.verdict)
                self.stdout.write(self.style.SUCCESS(f"  [OK] Submissão {sub_id} -> Prob {problem.index} [{problem.resolution_status}]"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar submissão {sub.get('id', 'Desconhecido')}: {e}"))
                continue