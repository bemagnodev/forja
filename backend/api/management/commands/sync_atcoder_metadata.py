import time
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from api.models import Contest, Problem, PlatformChoices
from api.services.atcoder_client import AtCoderClient

class Command(BaseCommand):
    help = 'Sincroniza os meta-dados estáticos (Contests e Problems) do AtCoder usando a The Kenkoooo API.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("Buscando metadados do AtCoder no Kenkoooo..."))
        client = AtCoderClient(timeout=30) 
        
        contests_data = client.get_contests()
        if not contests_data:
            self.stdout.write(self.style.ERROR("Nenhum contest retornado da API."))
            return
            
        self.stdout.write(f"  > Recebidos {len(contests_data)} contests. Salvando...")
        contests_created = 0
        
        existing_contests = set(Contest.objects.filter(
            platform=PlatformChoices.ATCODER
        ).values_list('platform_id', flat=True))
        
        for c in contests_data:
            platform_id = c.get('id')
            if not platform_id: continue
            
            if platform_id in existing_contests:
                continue
            
            
            start_epoch = c.get('start_epoch_second', 0) # tempo em Unix Time (segundos desde 1970)
            duration = c.get('duration_second', 0)
            title = c.get('title', platform_id)
            
            start_time = datetime.fromtimestamp(start_epoch, tz=timezone.UTC)
            
            _, created = Contest.objects.update_or_create(
                platform=PlatformChoices.ATCODER,
                platform_id=platform_id,
                defaults={
                    'name': title,
                    'start_time': start_time,
                    'duration_seconds': duration
                }
            )
            if created: contests_created += 1
            
        self.stdout.write(self.style.SUCCESS(f"Contests sincronizados! ({contests_created} novos)"))
        
        self.stdout.write(self.style.MIGRATE_HEADING("Buscando problemas do AtCoder..."))
        problems_data = client.get_problems()
        if not problems_data:
            self.stdout.write(self.style.ERROR("Nenhum problema retornado da API."))
            return
            
        self.stdout.write(f"  > Recebidos {len(problems_data)} problemas. Linkando aos Contests...")
        problems_created = 0
        
        existing_problems = set(Problem.objects.filter(
            platform=PlatformChoices.ATCODER
        ).values_list('platform_id', flat=True))
        
        contest_map = {
            c.platform_id: c for c in Contest.objects.filter(platform=PlatformChoices.ATCODER)
        }

        for p in problems_data:
            problem_id = p.get('id')
            if not problem_id: continue
                
            if problem_id in existing_problems:
                continue
                
                
            contest_id = p.get('contest_id')
            title = p.get('title', p.get('name', problem_id))
            
            # 1. Garantir que o prefixo não seja o próprio ID inútil (abc448_b - Make Target 2)
            if title.lower().startswith(f"{problem_id.lower()} - "):
                title = title[len(problem_id) + 3:]
            elif title.lower().startswith(f"{problem_id.lower()} "):
                title = title[len(problem_id) + 1:]
                
            # 2. Formatação Limpa (Ex "A - Watermelon" vira "A. Watermelon")
            if " - " in title:
                parts = title.split(" - ", 1)
                if len(parts[0]) <= 3:  # Provável que seja index tipo A, B, B1, Ex
                    title = f"{parts[0]}. {parts[1]}"
                    
            contest = contest_map.get(contest_id)
            
            _, created = Problem.objects.update_or_create(
                platform=PlatformChoices.ATCODER,
                platform_id=problem_id,
                defaults={
                    'title': title,
                    'contest': contest
                }
            )
            if created: problems_created += 1

        self.stdout.write(self.style.SUCCESS(f"Problemas sincronizados! ({problems_created} novos)"))
