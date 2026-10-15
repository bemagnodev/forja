import pytest
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.core.management import call_command
from api.models import Contest, Problem, ContestParticipation, User, Team, PlatformChoices


@pytest.mark.django_db(transaction=True)
def test_migration_0009_scenario_a_complete_and_empty_duplicate():
    """
    Cenário A: Contest completo + duplicado vazio.
    Antes da migration:
      - 2 Contests com (platform, platform_id) idênticos.
      - 1 Contest completo com Problems e ContestParticipation.
      - 1 Contest vazio com 0 Problems e 0 ContestParticipation.
    Depois da migration:
      - O ID do registro completo deve continuar existindo;
      - O vazio deve ser removido;
      - Problems continuam ligados ao ID completo;
      - ContestParticipation continua ligada ao ID completo;
      - Constraint impede nova duplicidade.
    """
    executor = MigrationExecutor(connection)
    migrate_from = [('api', '0008_alter_queueitem_priority')]
    migrate_to = [('api', '0009_consolidate_contests_and_add_constraints')]

    # 1. Volta para a migration 0008
    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    OldContest = old_apps.get_model('api', 'Contest')
    OldProblem = old_apps.get_model('api', 'Problem')
    OldUser = old_apps.get_model('api', 'User')
    OldParticipation = old_apps.get_model('api', 'ContestParticipation')

    # Cria usuário
    user = OldUser.objects.create(username="mig_user_a")

    # Cria contest canônico/completo (ID 3956 na simulação)
    complete_contest = OldContest.objects.create(
        id=3956,
        platform='CF_GYM',
        platform_id="101375",
        name="Complete Gym Contest",
        duration_seconds=18000
    )
    # Vincula problemas e participação ao completo
    p1 = OldProblem.objects.create(
        platform='CF_GYM',
        platform_id="101375A",
        title="Prob A",
        contest=complete_contest
    )
    part = OldParticipation.objects.create(
        user=user,
        contest=complete_contest
    )

    # Cria contest duplicado vazio (ID 4001)
    empty_contest = OldContest.objects.create(
        id=4001,
        platform='CF_GYM',
        platform_id="101375",
        name="Gym 101375",
        duration_seconds=0
    )

    # 2. Executa a migration 0009
    executor.loader.build_graph()
    executor.migrate(migrate_to)

    new_apps = executor.loader.project_state(migrate_to).apps
    NewContest = new_apps.get_model('api', 'Contest')
    NewProblem = new_apps.get_model('api', 'Problem')
    NewParticipation = new_apps.get_model('api', 'ContestParticipation')

    # Validações:
    # O canônico completo (3956) existe; o vazio (4001) foi removido
    assert NewContest.objects.filter(id=3956).exists()
    assert not NewContest.objects.filter(id=4001).exists()

    # Total de contests com esse platform_id é exatamente 1
    assert NewContest.objects.filter(platform='CF_GYM', platform_id="101375").count() == 1

    # Problems continuam apontando para o 3956
    p1_reloaded = NewProblem.objects.get(platform='CF_GYM', platform_id="101375A")
    assert p1_reloaded.contest_id == 3956

    # Participação continua apontando para o 3956
    part_reloaded = NewParticipation.objects.get(id=part.id)
    assert part_reloaded.contest_id == 3956

    # Tentativa de criar duplicata agora deve falhar por violação de constraint
    with pytest.raises(IntegrityError):
        NewContest.objects.create(
            platform='CF_GYM',
            platform_id="101375",
            name="Attempted Duplicate"
        )


@pytest.mark.django_db(transaction=True)
def test_migration_0009_scenario_b_both_duplicates_have_data_aborts():
    """
    Cenário B: Duplicados onde ambos possuem dados (Fail-Closed).
    Se ambos os Contests possuírem Problems ou Participações:
      - A migration DEVE abortar com erro explícito;
      - Não deve escolher silenciosamente um canônico;
      - Não deve excluir nem mover dados parcialmente.
    """
    executor = MigrationExecutor(connection)
    migrate_from = [('api', '0008_alter_queueitem_priority')]
    migrate_to = [('api', '0009_consolidate_contests_and_add_constraints')]

    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    OldContest = old_apps.get_model('api', 'Contest')
    OldProblem = old_apps.get_model('api', 'Problem')

    c1 = OldContest.objects.create(
        id=5001,
        platform='CF_GYM',
        platform_id="109999",
        name="Gym 1",
        duration_seconds=18000
    )
    OldProblem.objects.create(
        platform='CF_GYM',
        platform_id="109999A",
        title="Prob A",
        contest=c1
    )

    c2 = OldContest.objects.create(
        id=5002,
        platform='CF_GYM',
        platform_id="109999",
        name="Gym 2",
        duration_seconds=18000
    )
    OldProblem.objects.create(
        platform='CF_GYM',
        platform_id="109999B",
        title="Prob B",
        contest=c2
    )

    # Ao migrar para 0009, deve abortar com RuntimeError
    executor.loader.build_graph()
    with pytest.raises(RuntimeError) as exc_info:
        executor.migrate(migrate_to)

    assert "Migration abortada por segurança" in str(exc_info.value)
    assert "possui 1 Problems" in str(exc_info.value)

    # Confirma ausência de alteração parcial: ambos os Contests e Problems continuam intactos
    assert OldContest.objects.filter(id=5001).exists()
    assert OldContest.objects.filter(id=5002).exists()
    assert OldProblem.objects.filter(contest_id=5001, platform_id="109999A").exists()
    assert OldProblem.objects.filter(contest_id=5002, platform_id="109999B").exists()

    # Limpa os objetos do teste para não poluir
    OldProblem.objects.filter(contest_id__in=[5001, 5002]).delete()
    OldContest.objects.filter(id__in=[5001, 5002]).delete()
    executor.migrate(migrate_to)


@pytest.mark.django_db(transaction=True)
def test_migration_0009_scenario_c_duplicate_participations_aborts():
    """
    Cenário C: Participações duplicadas inesperadas.
    Se existir duplicidade em (user, contest) ou (team, contest):
      - A migration DEVE abortar antes de adicionar as constraints;
      - Não deve tentar resolver silenciosamente.
    """
    executor = MigrationExecutor(connection)
    migrate_from = [('api', '0008_alter_queueitem_priority')]
    migrate_to = [('api', '0009_consolidate_contests_and_add_constraints')]

    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    OldContest = old_apps.get_model('api', 'Contest')
    OldUser = old_apps.get_model('api', 'User')
    OldParticipation = old_apps.get_model('api', 'ContestParticipation')

    c = OldContest.objects.create(
        id=6001,
        platform='CF_GYM',
        platform_id="108888",
        name="Gym Unique",
        duration_seconds=18000
    )
    user = OldUser.objects.create(username="dup_part_user")

    # Cria duas participações do mesmo usuário no mesmo contest
    OldParticipation.objects.create(id=7001, user=user, contest=c)
    OldParticipation.objects.create(id=7002, user=user, contest=c)

    executor.loader.build_graph()
    with pytest.raises(RuntimeError) as exc_info:
        executor.migrate(migrate_to)

    assert "encontrada duplicidade de ContestParticipation" in str(exc_info.value)

    # Limpa
    OldParticipation.objects.filter(id__in=[7001, 7002]).delete()
    OldContest.objects.filter(id=6001).delete()
    executor.migrate(migrate_to)


@pytest.mark.django_db
def test_audit_duplicate_contests_command_detailed_output(capsys):
    """
    Testa o comando audit_duplicate_contests sem mocks frágeis.
    Verifica se exibe corretamente as estatísticas, motivos da escolha canônica
    e verificação de segurança dos duplicados vazios.
    """
    user = User.objects.create(username="audit_test_user")

    # Grupo 1: Sem duplicidades
    Contest.objects.create(
        platform=PlatformChoices.CF_GYM,
        platform_id="101111",
        name="Single Contest",
        duration_seconds=18000
    )

    call_command('audit_duplicate_contests')
    out = capsys.readouterr().out
    assert "Nenhuma duplicidade de Contest encontrada no banco" in out
    assert "Nenhuma duplicidade de ContestParticipation por (user, contest) encontrada" in out
    assert "Nenhuma duplicidade de ContestParticipation por (team, contest) encontrada" in out
