import pytest
from api.models import QueueItem


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
    assert item.is_completed is False
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
def test_queue_endpoints(api_client, base_user, sample_problem):
    """Testa a integração da API Ninja com a lógica da QueueItem"""
    # Create
    resp = api_client.post("/api/queue", data={
        "title": "Ler o livro de Grafos",
        "priority": "P1"
    }, content_type="application/json")
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Ler o livro de Grafos"
    item_id = data["id"]
    
    # Mudar priority inline (simulação na tabela)
    resp_put = api_client.post(f"/api/queue/{item_id}/priority", data={
        "priority": "P0"
    }, content_type="application/json")
    assert resp_put.status_code == 200
    assert resp_put.json()["priority"] == "P0"
    
    # Marcar como Completa
    resp_done = api_client.post(f"/api/queue/{item_id}/status", data={
        "is_completed": True
    }, content_type="application/json")
    assert resp_done.status_code == 200
    assert resp_done.json()["is_completed"] is True
    assert resp_done.json()["resolved_at"] is not None


@pytest.mark.django_db
def test_queue_priority_future(base_user):
    """Testa se a nova prioridade FUTURE foi adicionada corretamente no model e salva."""
    item = QueueItem.objects.create(
        user=base_user,
        title="Problema pro futuro",
        priority=QueueItem.Priority.FUTURE
    )
    assert item.priority == 'FUTURE'
    item.refresh_from_db()
    assert item.priority == 'FUTURE'


@pytest.mark.django_db
def test_queue_schema_fields(api_client, base_user, sample_problem):
    """Testa se os novos campos do QueueSchema (problem_title, contest_name, etc) funcionam"""
    QueueItem.objects.create(
        user=base_user,
        title="Estudo",
        priority=QueueItem.Priority.P1,
        linked_problem=sample_problem
    )
    resp = api_client.get("/api/queue")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    
    assert item["problem_title"] == "Math"
    assert item["contest_name"] == "Test Contest"
    assert item["ai_rating"] is None
    assert item["ai_tags"] == []
