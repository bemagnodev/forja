from django.db import migrations, models


def consolidate_duplicate_contests(apps, schema_editor):
    """
    Consolidação ultra-conservadora e determinística de Contests duplicados:
    1. Agrupa Contests por (platform, platform_id).
    2. Para cada grupo:
       - Ordena pela regra canônica estrita:
         a) maior contagem de Problems
         b) maior contagem de ContestParticipations
         c) maior completude de metadata (nome real, start_time preenchido, duration > 0)
         d) menor ID numérico (mais antigo)
       - O primeiro é eleito CANÔNICO.
       - Para todos os demais (duplicados):
         * VALIDAÇÃO FAIL-CLOSED: O duplicado DEVE conter ESTRITAMENTE 0 Problems e 0 ContestParticipations.
         * Se qualquer duplicado possuir Problems > 0 ou Participations > 0, ABORTA IMEDIATAMENTE com RuntimeError.
         * Sendo estritamente vazio, o duplicado é removido com segurança.
    3. Valida participações antes de aplicar constraints:
       - Se houver duplicidade em (user, contest) ou (team, contest), ABORTA IMEDIATAMENTE com RuntimeError.
    """
    Contest = apps.get_model('api', 'Contest')
    Problem = apps.get_model('api', 'Problem')
    ContestParticipation = apps.get_model('api', 'ContestParticipation')

    from django.db.models import Count

    # 1. Pré-validação de integridade de ContestParticipation
    user_part_dups = (
        ContestParticipation.objects.filter(user__isnull=False)
        .values('user_id', 'contest_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
        .order_by('user_id', 'contest_id')
    )
    if user_part_dups.exists():
        first_bad = user_part_dups.first()
        raise RuntimeError(
            f"Migration abortada: encontrada duplicidade de ContestParticipation para user_id={first_bad['user_id']}, contest_id={first_bad['contest_id']}."
        )

    team_part_dups = (
        ContestParticipation.objects.filter(team__isnull=False)
        .values('team_id', 'contest_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
        .order_by('team_id', 'contest_id')
    )
    if team_part_dups.exists():
        first_bad = team_part_dups.first()
        raise RuntimeError(
            f"Migration abortada: encontrada duplicidade de ContestParticipation para team_id={first_bad['team_id']}, contest_id={first_bad['contest_id']}."
        )

    # 2. Consolidação de Contests duplicados
    duplicates = (
        Contest.objects.values('platform', 'platform_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )

    for dup in duplicates:
        platform = dup['platform']
        platform_id = dup['platform_id']

        contests = list(Contest.objects.filter(platform=platform, platform_id=platform_id))

        def sort_key(c):
            p_count = Problem.objects.filter(contest_id=c.id).count()
            cp_count = ContestParticipation.objects.filter(contest_id=c.id).count()
            has_name = 1 if (c.name and not c.name.startswith("Gym ")) else 0
            has_start = 1 if c.start_time is not None else 0
            has_duration = 1 if (c.duration_seconds and c.duration_seconds > 0) else 0
            metadata_score = has_name + has_start + has_duration
            return (-p_count, -cp_count, -metadata_score, c.id)

        contests.sort(key=sort_key)
        canonical = contests[0]
        stale_contests = contests[1:]

        for stale in stale_contests:
            stale_p_count = Problem.objects.filter(contest_id=stale.id).count()
            stale_cp_count = ContestParticipation.objects.filter(contest_id=stale.id).count()

            # FAIL-CLOSED: se o duplicado tiver dados, não podemos deduzir merge automaticamente
            if stale_p_count > 0 or stale_cp_count > 0:
                raise RuntimeError(
                    f"Migration abortada por segurança: Contest duplicado ID {stale.id} ({platform}, {platform_id}) "
                    f"possui {stale_p_count} Problems e {stale_cp_count} ContestParticipations. "
                    f"A consolidação automática só é permitida para duplicados com 0 Problems e 0 Participations."
                )

            stale.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_alter_queueitem_priority'),
    ]

    operations = [
        migrations.RunPython(
            consolidate_duplicate_contests,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.AddConstraint(
            model_name='contest',
            constraint=models.UniqueConstraint(
                fields=('platform', 'platform_id'),
                name='unique_contest_platform_and_id'
            ),
        ),
        migrations.AddConstraint(
            model_name='contestparticipation',
            constraint=models.UniqueConstraint(
                condition=models.Q(user__isnull=False),
                fields=('user', 'contest'),
                name='unique_user_contest_participation'
            ),
        ),
        migrations.AddConstraint(
            model_name='contestparticipation',
            constraint=models.UniqueConstraint(
                condition=models.Q(team__isnull=False),
                fields=('team', 'contest'),
                name='unique_team_contest_participation'
            ),
        ),
    ]
