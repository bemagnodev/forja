import re
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from api.models import Contest, Problem, PlatformChoices
from api.services.codeforces_client import CodeforcesClient

class Command(BaseCommand):
    help = 'Sincroniza os meta-dados e problemas completos de Gyms do Codeforces onde o usuário possui submissões.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("Iniciando Sincronismo de CF Gyms baseados nos dados locais..."))
        
        # 1. Identificar Gyms Pendentes
        problems_without_contest = Problem.objects.filter(
            platform=PlatformChoices.CF_GYM, 
            contest__isnull=True
        )
        
        if not problems_without_contest.exists():
            self.stdout.write(self.style.SUCCESS("Nenhum problema de Gym órfão encontrado. Tudo em dia!"))
            return

        gym_ids = set()
        for p in problems_without_contest:
            # platform_id é algo como "104030A". Extraímos os números iniciais.
            m = re.match(r"^(\d+)", p.platform_id)
            if m:
                gym_ids.add(m.group(1))

        self.stdout.write(f"  > Foram identificados {len(gym_ids)} Gyms únicos a serem buscados: {', '.join(gym_ids)}")
        
        client = CodeforcesClient(timeout=30)
        gyms_created = 0
        problems_created = 0
        problems_updated = 0

        for gym_id in gym_ids:
            self.stdout.write(f"\nBuscando dados do Gym {gym_id}...")
            
            # Tratamento Gracioso para Gyms Privados ou com erro
            try:
                data = client.get_gym_standings(gym_id)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [!] Erro interno ao buscar Gym {gym_id}: {e}"))
                continue

            if not data:
                # O CodeforcesClient loga um comment ("is not visible" etc.) retornando None.
                self.stdout.write(self.style.WARNING(f"  [!] Não foi possível acessar o Gym {gym_id}. Pode ser privado ou não existir."))
                continue

            cf_contest = data.get('contest', {})
            cf_problems = data.get('problems', [])

            title = cf_contest.get('name', gym_id)
            start_epoch = cf_contest.get('startTimeSeconds')
            duration = cf_contest.get('durationSeconds', 0)
            
            start_time = None
            if start_epoch:
                start_time = datetime.fromtimestamp(start_epoch, tz=timezone.UTC)

            contest, c_created = Contest.objects.update_or_create(
                platform=PlatformChoices.CF_GYM,
                platform_id=gym_id,
                defaults={
                    'name': title,
                    'start_time': start_time,
                    'duration_seconds': duration
                }
            )
            
            if c_created: gyms_created += 1

            # Inserir o Catálogo Completo de Problemas do Gym
            # E atualizar o nosso problema orfão que engatilhou isso.
            
            for p in cf_problems:
                index = p.get('index', '')
                problem_id = f"{gym_id}{index}"
                name = p.get('name', '')
                p_title = f"{index}. {name}" if name else problem_id

                metadata = {
                    'rating': p.get('rating'),
                    'tags': p.get('tags', [])
                }

                _, p_created = Problem.objects.update_or_create(
                    platform=PlatformChoices.CF_GYM,
                    platform_id=problem_id,
                    defaults={
                        'title': p_title,
                        'contest': contest,
                        'platform_metadata': metadata
                    }
                )
                if p_created:
                    problems_created += 1
                else:
                    problems_updated += 1
            
            self.stdout.write(self.style.SUCCESS(f"  -> Sucesso: '{title}' ({len(cf_problems)} problemas syncados)"))

        self.stdout.write(self.style.MIGRATE_HEADING("\nResumo do Sincronismo Gym:"))
        self.stdout.write(self.style.SUCCESS(f"  Contests Criados: {gyms_created}"))
        self.stdout.write(self.style.SUCCESS(f"  Problemas Catalogo: {problems_created} novos, {problems_updated} atualizados"))
