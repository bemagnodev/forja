from ninja import NinjaAPI, Schema
from typing import List, Optional
from datetime import datetime
from django.db.models import Count
from .models import Submission, Problem, Contest, QueueItem, User

api = NinjaAPI(
    title="A Forja API",
    description="Backend de dados para análise de performance competitiva (CF + CSES)",
    version="1.0.0"
)

# === SCHEMAS  ===

class ContestSchema(Schema):
    name: str
    platform: str  # 'CF' ou 'CSES'

class ProblemSchema(Schema):
    name: str
    index: str      
    rating: Optional[int] = None  
    tags: List[str]
    is_solved: bool  
    contest: ContestSchema # Aninhamento: traz os dados do contest junto

class SubmissionSchema(Schema):
    submission_id: int
    verdict: str
    creation_time: datetime 
    problem: ProblemSchema

class StatsSchema(Schema):
    total_solved: int
    total_submissions: int
    total_contests: int
    platform_breakdown: dict  

class QueueSchema(Schema):
    id: int
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    linked_problem_id: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

class QueueCreateSchema(Schema):
    title: str
    description: Optional[str] = None
    priority: str = 'P2'
    linked_problem_id: Optional[int] = None

class QueueUpdatePrioritySchema(Schema):
    priority: str

class QueueUpdateStatusSchema(Schema):
    status: str

@api.get("/submissions", response=List[SubmissionSchema])
def list_submissions(request, limit: int = 20, offset: int = 0, platform: Optional[str] = None):
    """
    Retorna o histórico de submissões.
    Filtros: ?platform=CSES ou ?platform=CF
    Paginação: ?limit=10&offset=0
    """
    # 1. select related query_set, para evitar multiplas queries
    qs = Submission.objects.select_related('problem', 'problem__contest').order_by('-creation_time')
    
    # 2. Se o usuário pediu uma plataforma específica, filtra
    if platform:
        qs = qs.filter(problem__contest__platform=platform)
    
    # 3. define a paginação
    return qs[offset : offset + limit]

@api.get("/problems/solved", response=List[ProblemSchema])
def list_solved_problems(request, platform: Optional[str] = None):
    qs = Problem.objects.filter(is_solved=True).select_related('contest')
    
    if platform:
        qs = qs.filter(contest__platform=platform)
        
    return qs

@api.get("/stats", response=StatsSchema)
def get_stats(request):
    return {
        "total_solved": Problem.objects.filter(is_solved=True).count(),
        "total_submissions": Submission.objects.count(),
        "total_contests": Contest.objects.count(),
        "platform_breakdown": {
            "cf_solved": Problem.objects.filter(contest__platform='CF', is_solved=True).count(),
            "cses_solved": Problem.objects.filter(contest__platform='CSES', is_solved=True).count()
        }
    }

# === QUEUE / TRACKING ===

@api.get("/queue", response=List[QueueSchema])
def list_queue(request):
    """Retorna Fila Priorizada de problemas e sessões de estudo pendentes"""
    return QueueItem.objects.exclude(status='DONE').order_by('priority', '-created_at')

@api.post("/queue", response=QueueSchema)
def create_queue_item(request, payload: QueueCreateSchema):
    """Cria uma nova tarefa ou linka uma questão na fila de prioridade"""
    user = User.objects.first() # Setup mono-usuário temporário para MVP
    item = QueueItem.objects.create(
        user=user,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        linked_problem_id=payload.linked_problem_id
    )
    return item

@api.post("/queue/{item_id}/priority", response=QueueSchema)
def update_queue_priority(request, item_id: int, payload: QueueUpdatePrioritySchema):
    item = QueueItem.objects.get(id=item_id)
    item.priority = payload.priority
    item.save()
    return item

@api.post("/queue/{item_id}/status", response=QueueSchema)
def update_queue_status(request, item_id: int, payload: QueueUpdateStatusSchema):
    item = QueueItem.objects.get(id=item_id)
    item.status = payload.status
    if payload.status == 'DONE':
        from django.utils import timezone
        item.resolved_at = timezone.now()
    item.save()
    return item