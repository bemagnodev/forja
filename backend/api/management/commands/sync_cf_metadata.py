import time
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from api.models import Contest, Problem, PlatformChoices
from api.services.codeforces_client import CodeforcesClient
from api.services.problem_metadata import upsert_problem_metadata

class Command(BaseCommand):
    help = 'Sincroniza os meta-dados estáticos do Codeforces (Contests e Problems) usando a API Oficial.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("Buscando metadados globais da Codeforces API..."))
        client = CodeforcesClient(timeout=30) 
        
        # 1. Contests
        contests_data = client.get_contests()
        if not contests_data:
            self.stdout.write(self.style.ERROR("Nenhum contest retornado ou erro de conexão."))
            return
            
        self.stdout.write(f"  > Recebidos {len(contests_data)} contests. Salvando...")
        contests_created = 0
        
        # Otimização Incremental O(1)
        existing_contests = set(Contest.objects.filter(
            platform__in=[PlatformChoices.CF_OFFICIAL, PlatformChoices.CF_GYM]
        ).values_list('platform_id', flat=True))
        
        for c in contests_data:
            contest_id = str(c.get('id'))
            title = c.get('name', contest_id)
            start_epoch = c.get('startTimeSeconds')
            duration = c.get('durationSeconds', 0)
            
            start_time = None
            if start_epoch:
                start_time = datetime.fromtimestamp(start_epoch, tz=timezone.UTC)
            is_gym = int(contest_id) >= 100000
            platform_type = PlatformChoices.CF_GYM if is_gym else PlatformChoices.CF_OFFICIAL
            
            # Incremental: Ignorar se já existe no banco e o contest encerrou.
            if contest_id in existing_contests and c.get('phase') == 'FINISHED':
                continue
                
            _, created = Contest.objects.update_or_create(
                platform=platform_type,
                platform_id=contest_id,
                defaults={
                    'name': title,
                    'start_time': start_time,
                    'duration_seconds': duration
                }
            )
            if created: contests_created += 1
            
        self.stdout.write(self.style.SUCCESS(f"Contests sincronizados! ({contests_created} novos)"))
        
        # 2. Problems
        self.stdout.write(self.style.MIGRATE_HEADING("Buscando gama de problemas do Codeforces..."))
        problems_full_data = client.get_problems()
        problems_data = problems_full_data.get('problems', [])
        
        if not problems_data:
            self.stdout.write(self.style.ERROR("Nenhum problema retornado da API."))
            return
            
        self.stdout.write(f"  > Recebidos {len(problems_data)} problemas. Injetando dados ricos e tags JSON...")
        problems_created = 0
        
        # Otimização Incremental O(1)
        existing_problems = set(Problem.objects.filter(
            platform__in=[PlatformChoices.CF_OFFICIAL, PlatformChoices.CF_GYM]
        ).values_list('platform_id', flat=True))
        
        contest_map = {
            c.platform_id: c for c in Contest.objects.filter(platform__in=[PlatformChoices.CF_OFFICIAL, PlatformChoices.CF_GYM])
        }
    
        for p in problems_data:
            contest_id_num = p.get('contestId')
            if not contest_id_num: continue
            
            contest_id = str(contest_id_num)
            index = p.get('index', '')
            name = p.get('name', '')
            
            problem_id = f"{contest_id}{index}"
            if problem_id in existing_problems:
                continue # Incremental O(1) Pula transações inúteis

            title = f"{index}. {name}" if name else problem_id
            
            # MAGIA: Injetar rating e tags nativamente da API do CF no model que criamos para escalar IA
            metadata = {
                'rating': p.get('rating'),
                'tags': p.get('tags', [])
            }
            
            contest = contest_map.get(contest_id)
            
            is_gym = int(contest_id) >= 100000
            platform_type = PlatformChoices.CF_GYM if is_gym else PlatformChoices.CF_OFFICIAL
            
            _, created = upsert_problem_metadata(
                platform=platform_type,
                platform_id=problem_id,
                fields={
                    'title': title,
                    'contest': contest,
                },
                metadata=metadata,
            )
            if created: problems_created += 1

        self.stdout.write(self.style.SUCCESS(f"Problemas Codeforces hidratados com Rating e Tags! ({problems_created} novos)"))
