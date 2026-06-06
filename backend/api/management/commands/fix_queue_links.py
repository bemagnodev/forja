from django.core.management.base import BaseCommand
from api.models import Problem, QueueItem, PlatformChoices
from api.services.atcoder_client import AtCoderClient


class Command(BaseCommand):
    help = (
        "Corrige dois problemas de dados:\n"
        "1) Enriquece títulos de Problem AtCoder que ainda usam platform_id como fallback.\n"
        "2) Vincula QueueItems órfãos (sem linked_problem) ao Problem correto via busca por título/platform_id."
    )

    def handle(self, *args, **kwargs):
        self._enrich_atcoder_titles()
        self._link_orphan_queue_items()

    # ── Passo 1: Enriquecer títulos AtCoder ──────────────────────────────────

    def _enrich_atcoder_titles(self):
        """
        Busca todos os Problem AtCoder cujo title == platform_id (fallback do sync)
        e atualiza com o título real da API Kenkoooo (resources/problems.json).
        """
        self.stdout.write(self.style.MIGRATE_HEADING("\n[Passo 1] Enriquecendo títulos AtCoder..."))

        # Filtra apenas os problemas que ainda têm title == platform_id
        orphan_titles = Problem.objects.filter(platform=PlatformChoices.ATCODER)
        orphan_titles = [p for p in orphan_titles if p.title == p.platform_id]

        if not orphan_titles:
            self.stdout.write("  > Nenhum problema AtCoder com título fallback encontrado. Nada a fazer.")
            return

        self.stdout.write(f"  > {len(orphan_titles)} problems com título = platform_id. Buscando títulos reais...")

        # Baixa o JSON completo de problemas do Kenkoooo
        client = AtCoderClient()
        problems_data = client.get_problems()

        if not problems_data:
            self.stdout.write(self.style.ERROR("  > Falha ao buscar problems.json da Kenkoooo API."))
            return

        # Cria um índice { platform_id -> title } para O(1) lookup
        title_map = {p['id']: p['title'] for p in problems_data if 'id' in p and 'title' in p}
        self.stdout.write(f"  > {len(title_map)} títulos carregados da API.")

        updated = 0
        for problem in orphan_titles:
            real_title = title_map.get(problem.platform_id)
            if real_title:
                problem.title = real_title
                problem.save(update_fields=['title'])
                updated += 1
                self.stdout.write(f"    OK {problem.platform_id} => {real_title!r}")
            else:
                self.stdout.write(f"    MISS {problem.platform_id} nao encontrado na API")

        self.stdout.write(self.style.SUCCESS(f"  > Passo 1 concluído! {updated} títulos atualizados."))

    # ── Passo 2: Vincular QueueItems órfãos ──────────────────────────────────

    def _link_orphan_queue_items(self):
        """
        Tenta vincular QueueItems que têm source_platform mas linked_problem=None.
        Estratégia de match:
         1. Tenta encontrar Problem pelo platform_id exato (item.title pode ser o ID)
         2. Tenta encontrar Problem pelo título exato (case-insensitive)
        """
        self.stdout.write(self.style.MIGRATE_HEADING("\n[Passo 2] Vinculando QueueItems órfãos..."))

        # Apenas itens com plataforma definida mas sem link
        orphans = QueueItem.objects.filter(
            source_platform__isnull=False,
            linked_problem__isnull=True,
            item_type='PROBLEM'
        )

        if not orphans.exists():
            self.stdout.write("  > Nenhum QueueItem órfão encontrado. Nada a fazer.")
            return

        self.stdout.write(f"  > {orphans.count()} itens para tentar vincular.")

        linked = 0
        skipped = 0

        for item in orphans:
            # Mapeia a platform do QueueItem para o platform do Problem
            platform_map = {
                'CODEFORCES': ['CF_OFFICIAL', 'CF_GYM'],
                'ATCODER': ['ATCODER'],
                'CSES': ['CSES'],
            }
            target_platforms = platform_map.get(item.source_platform, [item.source_platform])

            # Tentativa 1: título do item == platform_id do Problem
            problem = Problem.objects.filter(
                platform__in=target_platforms,
                platform_id__iexact=item.title
            ).first()

            # Tentativa 2: título do item == título do Problem (case-insensitive)
            if not problem:
                problem = Problem.objects.filter(
                    platform__in=target_platforms,
                    title__iexact=item.title
                ).first()

            if problem:
                item.linked_problem = problem
                item.save(update_fields=['linked_problem'])
                linked += 1
                self.stdout.write(f"    OK QueueItem {item.id!r} ({item.title!r}) => Problem {problem.platform_id!r}")
            else:
                skipped += 1
                self.stdout.write(f"    MISS QueueItem {item.id!r} ({item.title!r}) -- sem match no banco")

        self.stdout.write(self.style.SUCCESS(
            f"  > Passo 2 concluído! {linked} vinculados, {skipped} sem match."
        ))
