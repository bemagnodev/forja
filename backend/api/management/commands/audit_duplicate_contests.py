from django.core.management.base import BaseCommand
from django.db.models import Count
from api.models import Contest, ContestParticipation, Problem


def get_canonical_sort_key(c, problems_count, participations_count):
    """
    Regra canônica única para Contest:
    1. maior quantidade de Problems
    2. maior quantidade de ContestParticipations
    3. maior completude de metadata (nome não vazio, start_time não nulo, duration_seconds > 0)
    4. desempate determinístico por menor ID (registro original)
    """
    has_name = 1 if (c.name and not c.name.startswith("Gym ")) else 0
    has_start = 1 if c.start_time is not None else 0
    has_duration = 1 if (c.duration_seconds and c.duration_seconds > 0) else 0
    metadata_score = has_name + has_start + has_duration

    # Queremos: maior problems_count, maior participations_count, maior metadata_score, menor ID
    return (
        -problems_count,
        -participations_count,
        -metadata_score,
        c.id
    )


class Command(BaseCommand):
    help = "Audita duplicidades de Contest por (platform, platform_id) e participações duplicadas (Read-Only)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== AUDITORIA DE CONTESTS E PARTICIPAÇÕES DUPLICADAS (READ-ONLY) ==="))

        # 1. Auditoria de Contests duplicados
        duplicates = (
            Contest.objects.values('platform', 'platform_id')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
            .order_by('platform', 'platform_id')
        )

        total_groups = duplicates.count()
        if not total_groups:
            self.stdout.write(self.style.SUCCESS("[OK] Nenhuma duplicidade de Contest encontrada no banco."))
        else:
            self.stdout.write(self.style.WARNING(f"[!] Encontrados {total_groups} grupos de contests duplicados por (platform, platform_id):\n"))

            for group in duplicates:
                platform = group['platform']
                platform_id = group['platform_id']
                contests = list(Contest.objects.filter(
                    platform=platform,
                    platform_id=platform_id
                ))

                # Coleta métricas de cada contest
                contest_metrics = []
                for c in contests:
                    p_count = c.problems.count()
                    cp_count = c.participations.count()
                    key = get_canonical_sort_key(c, p_count, cp_count)
                    contest_metrics.append((key, c, p_count, cp_count))

                contest_metrics.sort(key=lambda x: x[0])

                canonical_tuple = contest_metrics[0]
                canonical = canonical_tuple[1]
                canonical_p_count = canonical_tuple[2]
                canonical_cp_count = canonical_tuple[3]
                duplicates_tuples = contest_metrics[1:]

                self.stdout.write(f"Plataforma: {platform} | Platform ID: {platform_id}")
                reason = f"{canonical_p_count} problems, {canonical_cp_count} participações, metadata (start={'SIM' if canonical.start_time else 'NÃO'}, dur={canonical.duration_seconds}s)"
                self.stdout.write(self.style.SUCCESS(
                    f"  * Canônico Escolhido: ID {canonical.id} | Nome: {canonical.name} | Duração: {canonical.duration_seconds}s | "
                    f"Start: {'SIM' if canonical.start_time else 'NÃO'} | Problems: {canonical_p_count} | Participações: {canonical_cp_count} | Motivo: {reason}"
                ))

                for dt in duplicates_tuples:
                    dup = dt[1]
                    p_count = dt[2]
                    cp_count = dt[3]
                    is_safe = (p_count == 0 and cp_count == 0)
                    safety_str = "SEGURO PARA EXCLUSÃO (0 problems, 0 participations)" if is_safe else "PERIGO: CONTÉM DADOS!"
                    style_fn = self.style.WARNING if is_safe else self.style.ERROR

                    self.stdout.write(style_fn(
                        f"    - Duplicado: ID {dup.id} | Nome: {dup.name} | Duração: {dup.duration_seconds}s | "
                        f"Start: {'SIM' if dup.start_time else 'NÃO'} | Problems: {p_count} | Participações: {cp_count} | {safety_str}"
                    ))

                self.stdout.write("")

        # 2. Auditoria de Participações Duplicadas (user, contest)
        user_part_dups = (
            ContestParticipation.objects.filter(user__isnull=False)
            .values('user', 'contest')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
        )
        if user_part_dups.exists():
            self.stdout.write(self.style.ERROR(f"[!] ENCONTRADAS {user_part_dups.count()} PARTICIPAÇÕES DUPLICADAS POR (user, contest)!"))
            for upd in user_part_dups:
                self.stdout.write(f"    - User ID: {upd['user']} | Contest ID: {upd['contest']} | Total: {upd['total']}")
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Nenhuma duplicidade de ContestParticipation por (user, contest) encontrada."))

        # 3. Auditoria de Participações Duplicadas (team, contest)
        team_part_dups = (
            ContestParticipation.objects.filter(team__isnull=False)
            .values('team', 'contest')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
        )
        if team_part_dups.exists():
            self.stdout.write(self.style.ERROR(f"[!] ENCONTRADAS {team_part_dups.count()} PARTICIPAÇÕES DUPLICADAS POR (team, contest)!"))
            for tpd in team_part_dups:
                self.stdout.write(f"    - Team ID: {tpd['team']} | Contest ID: {tpd['contest']} | Total: {tpd['total']}")
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Nenhuma duplicidade de ContestParticipation por (team, contest) encontrada."))

        self.stdout.write(self.style.SUCCESS("\nAuditoria concluída com sucesso."))
