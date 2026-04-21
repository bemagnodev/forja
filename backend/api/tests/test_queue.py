import pytest
from datetime import datetime
from api.models import User, QueueItem, Problem, Contest

@pytest.fixture
def base_user():
    return User.objects.create(username="mentor")

@pytest.fixture
def sample_problem():
    contest = Contest.objects.create(platform='CF', platform_id='1000', name='Test Contest')
    return Problem.objects.create(platform='CF', platform_id='1000A', title='Math', contest=contest)

@pytest.mark.django_db
def test_create_queue_item_standalone(base_user):
    """Testa se a Fila aceita uma sessão de estudos puramente teórica (sem Problem)"""
    item = QueueItem.objects.create(
        user=base_user,
        title="Estudar Segment Tree",
        priority=QueueItem.Priority.P0
    )
    assert item.title == "Estudar Segment Tree"
    assert item.linked_problem is None
    assert item.status == QueueItem.Status.TODO
    assert item.priority == 'P0'

@pytest.mark.django_db
def test_create_queue_item_linked(base_user, sample_problem):
    """Testa se a Fila suporta a lincagem técnica com problemas reais do tracker"""
    item = QueueItem.objects.create(
        user=base_user,
        title="(CF) Math Upsolving",
        priority=QueueItem.Priority.UPSOLVING,
        linked_problem=sample_problem
    )
    assert item.linked_problem.platform_id == '1000A'
    assert item.priority == 'UPSOLVING'

@pytest.mark.django_db
def test_queue_endpoints(client, base_user, sample_problem):
    """Testa a integração da API Ninja com a lógica da QueueItem"""
    # Create
    resp = client.post("/api/queue", data={
        "title": "Ler o livro de Grafos",
        "priority": "P1"
    }, content_type="application/json")
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Ler o livro de Grafos"
    item_id = data["id"]
    
    # Mudar priority inline (simulação na tabela)
    resp_put = client.post(f"/api/queue/{item_id}/priority", data={
        "priority": "P0"
    }, content_type="application/json")
    assert resp_put.status_code == 200
    assert resp_put.json()["priority"] == "P0"
    
    # Marcar como Completa
    resp_done = client.post(f"/api/queue/{item_id}/status", data={
        "status": "DONE"
    }, content_type="application/json")
    assert resp_done.status_code == 200
    assert resp_done.json()["status"] == "DONE"
    assert resp_done.json()["resolved_at"] is not None
