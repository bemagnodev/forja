import pytest
from api.models import User, Problem, UserProblemTracking, PlatformChoices

@pytest.mark.django_db
def test_fsm_promotion_to_done():
    """
    Cenário: O usuário marca um problema como DOABLE (na fila para resolver) e o ETL detecta que ele recebeu um Accepted (AC) na plataforma.
    Resultado Esperado: O sistema "recompensa" o usuário promovendo automaticamente o review_status para DONE.
    """
    user = User.objects.create(username="test_user")
    problem = Problem.objects.create(platform=PlatformChoices.CF_OFFICIAL, platform_id="100A", title="Watermelon")
    
    # Usuário marca problema manualmente como DOABLE (na fila pra resolver)
    tracker = UserProblemTracking.objects.create(
        user=user,
        problem=problem,
        review_status=UserProblemTracking.ReviewStatus.DOABLE
    )
    
    # ETL sync rodou e percebeu um AC no sistema
    tracker.system_status = UserProblemTracking.SystemStatus.PRACTICE_AC
    tracker.save() # Dispara a FSM _sync_system_to_review
    
    tracker.refresh_from_db()
    assert tracker.review_status == UserProblemTracking.ReviewStatus.DONE

@pytest.mark.django_db
def test_fsm_promotion_to_doable_if_wa():
    """
    Cenário: O usuário nunca abriu a questão (PENDING_TRIAGE), mas tenta enviá-la e recebe um Erro (PRACTICE_WA).
    Resultado Esperado: O sistema entende que ele já está ativamente tentando esse problema, portanto, move da Triagem para DOABLE.
    """
    user = User.objects.create(username="test_user")
    problem = Problem.objects.create(platform=PlatformChoices.CF_OFFICIAL, platform_id="100B", title="Test")
    
    # Cria o tracker já injetando system_status='PRACTICE_WA' com review_status UNATTEMPTED
    tracker = UserProblemTracking.objects.create(
        user=user,
        problem=problem,
        review_status=UserProblemTracking.ReviewStatus.PENDING_TRIAGE,
        system_status=UserProblemTracking.SystemStatus.PRACTICE_WA
    )
    
    tracker.refresh_from_db()
    assert tracker.review_status == UserProblemTracking.ReviewStatus.DOABLE

@pytest.mark.django_db
def test_ignored_to_done_on_ac():
    """
    Cenário: O usuário marcou uma questão como IGNORED. 
    1. Mais tarde, ele envia um código que dá WA.
    2. Eventualmente, ele envia um código e tira AC.
    Resultado Esperado: 
    1. O WA bate no "Escudo" e a questão continua IGNORED.
    2. O AC quebra o Escudo e promove definitivamente a questão para DONE.
    """
    user = User.objects.create(username="test_user")
    problem = Problem.objects.create(platform=PlatformChoices.CF_OFFICIAL, platform_id="100C", title="Logic")
    
    # IGNORED explícito pelo Humano
    tracker = UserProblemTracking.objects.create(
        user=user,
        problem=problem,
        review_status=UserProblemTracking.ReviewStatus.IGNORED
    )
    
    # Submete WA 
    tracker.system_status = UserProblemTracking.SystemStatus.PRACTICE_WA
    tracker.save()
    
    # FSM deve proteger o IGNORED e não transformar em DOABLE
    tracker.refresh_from_db()
    assert tracker.review_status == UserProblemTracking.ReviewStatus.IGNORED
    
    # Magicamente deu AC. FSM DEVE sobrepor tudo e cravar DONE.
    tracker.system_status = UserProblemTracking.SystemStatus.PRACTICE_AC
    tracker.save()
    tracker.refresh_from_db()
    assert tracker.review_status == UserProblemTracking.ReviewStatus.DONE

@pytest.mark.django_db
def test_manual_done_promotes_system_to_upsolved():
    """
    Cenário (Reatividade Humana): Em um problema nunca tentado na plataforma, o usuário marca como DONE manualmente.
    Resultado Esperado: O sistema entende que foi concluído pelo usuário de forma paralela, alterando o system_status para UPSOLVED automaticamente, sem voltar para pendente quando removido. (O teste foi ajustado para focar só na ida para o DONE, pois decidimos não reverter automaticamente pra PENDING_UPSOLVED).
    """
    user = User.objects.create(username="test_user")
    problem = Problem.objects.create(platform=PlatformChoices.CF_OFFICIAL, platform_id="100D", title="Human Power")
    
    # Cria sem mexer (UNATTEMPTED e PENDING_TRIAGE padrão)
    tracker = UserProblemTracking.objects.create(
        user=user, 
        problem=problem,
        system_status=UserProblemTracking.SystemStatus.UNATTEMPTED
    )

    # Usuário atua na plataforma e marca DONE
    tracker.review_status = UserProblemTracking.ReviewStatus.DONE
    tracker.save()

    # FSM deve promover o system_status puxando do Admin para o Técnico
    tracker.refresh_from_db()
    assert tracker.system_status == UserProblemTracking.SystemStatus.UPSOLVED

@pytest.mark.django_db
def test_protection_maintains_done_on_future_wa():
    """
    Cenário (Proteção Histórica): O problema JÁ FOI conquistado (DONE e SOLVED_LIVE no passado). Dias depois o ETL importa um 'WA' acidental em um teste extra.
    Resultado Esperado: O review_status NUNCA pode ser rebaixado de DONE para DOABLE porque já foi finalizado no passado.
    """
    user = User.objects.create(username="test_user")
    problem = Problem.objects.create(platform=PlatformChoices.CF_OFFICIAL, platform_id="100E", title="Safe Question")
    
    # Já temos o sucesso consolidado no banco
    tracker = UserProblemTracking.objects.create(
        user=user, 
        problem=problem,
        review_status=UserProblemTracking.ReviewStatus.DONE,
        system_status=UserProblemTracking.SystemStatus.SOLVED_LIVE
    )

    # Caiu um WA via Sync Pipeline
    tracker.system_status = UserProblemTracking.SystemStatus.PRACTICE_WA
    tracker.save()

    # A FSM com seu is_protected deve bloquear o rebaixamento
    tracker.refresh_from_db()
    assert tracker.review_status == UserProblemTracking.ReviewStatus.DONE
