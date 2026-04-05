import pytest
from api.models import User, Problem, UserProblemTracking, PlatformChoices

@pytest.mark.django_db
def test_fsm_promotion_to_done():
    user = User.objects.create(username="test_user")
    problem = Problem.objects.create(platform=PlatformChoices.CF_OFFICIAL, platform_id="100A", title="Watermelon")
    
    # Usuário marca problema manualmente como DOABLE (na fila pra resolver)
    tracker = UserProblemTracking.objects.create(
        user=user,
        problem=problem,
        review_status=UserProblemTracking.ReviewStatus.DOABLE
    )
    
    # ETL sync rodou e percebeu um AC
    tracker.system_status = UserProblemTracking.SystemStatus.PRACTICE_AC
    tracker.save() # Dispara a FSM _sync_system_to_review
    
    tracker.refresh_from_db()
    assert tracker.review_status == UserProblemTracking.ReviewStatus.DONE

@pytest.mark.django_db
def test_fsm_promotion_to_doable_if_wa():
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
