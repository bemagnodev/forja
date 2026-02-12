from django.core.management.base import BaseCommand
from api.models import Contest, Problem, Submission
import requests
import time
from datetime import datetime, timezone

class Command(BaseCommand):
    help = 'Importa TODO o histórico do Codeforces com parada inteligente'

    def add_arguments(self, parser):
        parser.add_argument('--handle', type=str, help='Handle do usuário')

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

    def handle(self, *args, **options):
        handle = options['handle'] or 'bemagno'
        self.stdout.write(f"Iniciando ETL para: {handle}...")

        start_index = 1
        batch_size = 100 # Pega de 100 em 100
        keep_fetching = True

        while keep_fetching:
            self.stdout.write(f" Buscando submissões {start_index} até {start_index + batch_size}...")
            url = f"https://codeforces.com/api/user.status?handle={handle}&from={start_index}&count={batch_size}"
            
            try:
                response = requests.get(url, timeout=10)
                
                # === DEBUG ===
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"Erro HTTP: {response.status_code}"))
                    self.stdout.write(f"Conteúdo recebido: {response.text[:500]}") # Mostra o começo do erro
                    break

                try:
                    data = response.json()
                except ValueError:
                    self.stdout.write(self.style.ERROR("A API retornou algo que não é JSON (provavelmente HTML)."))
                    self.stdout.write(f"Conteúdo: {response.text[:200]}")
                    break

                if data['status'] != 'OK':
                    self.stdout.write(self.style.ERROR(f"Erro na API: {data.get('comment')}"))
                    break

                submissions = data['result']
                
                # Se a lista vier vazia, acabaram as submissões do histórico
                if not submissions:
                    self.stdout.write(self.style.SUCCESS("Fim do histórico encontrado."))
                    break

                for sub in submissions:
                    sub_id = sub['id']

                    # Se essa submissão já existe, significa que daqui para trás já importamos tudo.
                    if Submission.objects.filter(submission_id=sub_id).exists():
                        self.stdout.write(self.style.SUCCESS(f"Submissão {sub_id} já existe. Parando importação incremental."))
                        keep_fetching = False # Sai do while
                        break # Sai do for

                    # Aviso de Contest Fantasma
                    if 'contestId' not in sub:
                        self.stdout.write(self.style.WARNING(f"Submissão {sub_id} ignorada (Sem contestId - Provável Gym/Mashup antigo)"))
                        continue

                    # === Lógica de contests em grupo ===
                    contest_id = sub['contestId']
                    
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

                    # Busca o nome real do contest na API
                    if created_contest:
                        real_name = self.get_contest_name(contest_id)
                        contest.name = real_name
                        contest.save()
                        self.stdout.write(f"  Contest novo cadastrado: {real_name}")
                        time.sleep(0.5) # Pausa para não bloquear a API 

                    # === Lógica de problema ===
                    prob_data = sub['problem']
                    problem, _ = Problem.objects.get_or_create(
                        contest=contest,
                        index=prob_data['index'],
                        defaults={
                            'name': prob_data['name'],
                            'rating': prob_data.get('rating'),
                            'tags': prob_data.get('tags', [])
                        }
                    )

                    # === Lógica de submissão ===
                    if sub.get('verdict') == 'OK' and is_team_submission:
                        problem.solved_by_team = True
                        problem.save()

                    dt = datetime.fromtimestamp(sub['creationTimeSeconds'], tz=timezone.utc)
                    
                    Submission.objects.create(
                        problem=problem,
                        submission_id=sub_id,
                        verdict=sub.get('verdict', 'TESTING'),
                        creation_time=dt,
                    )

                    if sub.get('verdict') == 'OK':
                        if not problem.is_solved:
                            problem.is_solved = True
                            problem.save()
                    
                    self.stdout.write(self.style.SUCCESS(f"  + Submissão {sub_id} importada."))

                # Avança para a próxima página
                start_index += batch_size
                time.sleep(1)  # Pausa para não bloquear a API

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro Crítico: {e}"))
                break