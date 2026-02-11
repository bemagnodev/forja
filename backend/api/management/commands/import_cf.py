from django.core.management.base import BaseCommand
from api.models import Contest, Problem, Submission
import requests
from datetime import datetime, timezone

class Command(BaseCommand):
    help = 'Importa submissões do Codeforces para o Banco de Dados'

    def add_arguments(self, parser):
        # Permite passar o handle como argumento: python manage.py import_cf --handle BernardoO
        parser.add_argument('--handle', type=str, help='Handle do usuário no Codeforces')

    def handle(self, *args, **options):
        handle = options['handle'] or 'BernardoO' # Seu default
        self.stdout.write(f"Buscando dados para: {handle}...")

        url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=50" # Pegando as últimas 50
        
        try:
            response = requests.get(url)
            data = response.json()

            if data['status'] != 'OK':
                self.stdout.write(self.style.ERROR(f"Erro na API: {data.get('comment')}"))
                return

            submissions = data['result']
            
            for sub in submissions:
                # 1. Pular se não tiver contestId (ex: problemas soltos de gym)
                if 'contestId' not in sub:
                    continue

                # 2. Criar ou Pegar o Contest
                contest_id = sub['contestId']
                contest, created = Contest.objects.get_or_create(
                    external_id=contest_id,
                    defaults={
                        'name': f"Contest {contest_id}", # Placeholder até pegarmos o nome real
                        'is_team': False 
                    }
                )

                # 3. Criar ou Pegar o Problema
                prob_data = sub['problem']
                problem, created = Problem.objects.get_or_create(
                    contest=contest,
                    index=prob_data['index'],
                    defaults={
                        'name': prob_data['name'],
                        'rating': prob_data.get('rating'),
                        'tags': prob_data.get('tags', [])
                    }
                )

                # 4. Criar ou Atualizar a Submissão
                # Timestamp do CF vem em segundos, precisamos converter
                dt = datetime.fromtimestamp(sub['creationTimeSeconds'], tz=timezone.utc)
                
                submission, created = Submission.objects.update_or_create(
                    submission_id=sub['id'],
                    defaults={
                        'problem': problem,
                        'submission_id': sub['id'], # redundante mas ok
                        'verdict': sub.get('verdict', 'TESTING'),
                        'creation_time': dt,
                        'is_upsolved': False # Lógica futura
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Nova submissão: {problem.name} ({sub.get('verdict')})"))
            
            self.stdout.write(self.style.SUCCESS("Importação concluída com sucesso!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro Crítico: {e}"))