import re
from django.core.management.base import BaseCommand
from api.models import Problem, PlatformChoices
from api.services.codeforces_client import CodeforcesClient
from api.services.codeforces_gym_service import ensure_codeforces_gym_metadata


class Command(BaseCommand):
    help = (
        'Sincroniza os metadados e problemas completos de Gyms do Codeforces baseando-se em '
        'problemas CF_GYM órfãos locais (contest__isnull=True). '
        'Atenção: atualmente descobre apenas problemas órfãos, não varre contests já existentes incompletos.'
    )

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("Iniciando Sincronismo de CF Gyms baseados nos dados locais..."))
        
        # 1. Identificar Gyms Pendentes
        # Nota pedagógica: este comando foca especificamente na recuperação de problemas órfãos.
        # Contests incompletos que já possuam problemas associados não são descobertos por esta consulta.
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
            sync_result = ensure_codeforces_gym_metadata(gym_id, client=client)
            if not sync_result or not sync_result.contest:
                self.stdout.write(self.style.WARNING(f"  [!] Não foi possível acessar o Gym {gym_id}. Pode ser privado ou não existir."))
                continue

            if sync_result.contest_created:
                gyms_created += 1
            problems_created += sync_result.problems_created
            problems_updated += sync_result.problems_updated

            num_problems = Problem.objects.filter(contest=sync_result.contest).count()
            self.stdout.write(self.style.SUCCESS(f"  -> Sucesso: '{sync_result.contest.name}' ({num_problems} problemas syncados)"))

        self.stdout.write(self.style.MIGRATE_HEADING("\nResumo do Sincronismo Gym:"))
        self.stdout.write(self.style.SUCCESS(f"  Contests Criados: {gyms_created}"))
        self.stdout.write(self.style.SUCCESS(f"  Problemas Catalogo: {problems_created} novos, {problems_updated} atualizados"))
