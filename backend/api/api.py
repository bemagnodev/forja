from ninja import NinjaAPI, Schema
from typing import List, Optional
from datetime import datetime
from django.db.models import Count
from .models import Submission, Problem, Contest, QueueItem, User, UserProblemTracking

api = NinjaAPI(
    title="A Forja API",
    description="Backend de dados para análise de performance competitiva+",
    version="1.0.0",
    urls_namespace="api",
)

# === SCHEMAS  ===

class ContestSchema(Schema):
    name: str
    platform: str  # 'CF' ou 'CSES'

class ProblemTrackingSchema(Schema):
    system_status: str
    review_status: str

class ProblemSchema(Schema):
    id: int
    name: str 
    index: str      
    rating: Optional[int] = None  
    tags: List[str] = []
    tracking: Optional[ProblemTrackingSchema] = None
    contest: ContestSchema

    @staticmethod
    def resolve_name(obj):
        return obj.title

    @staticmethod
    def resolve_index(obj):
        return obj.platform_id

    @staticmethod
    def resolve_rating(obj):
        return obj.platform_metadata.get('rating')

    @staticmethod
    def resolve_tags(obj):
        return obj.platform_metadata.get('tags', [])

    @staticmethod
    def resolve_tracking(obj):
        user = User.objects.first()
        return obj.user_trackings.filter(user=user).first()

class SubmissionSchema(Schema):
    id: int
    verdict: str
    creation_time: datetime 
    problem: ProblemSchema

    @staticmethod
    def resolve_id(obj):
        return obj.id

class StatsSchema(Schema):
    total_solved: int
    total_submissions: int
    total_contests: int
    platform_breakdown: dict  

class QueueSchema(Schema):
    id: int
    item_type: str
    title: str
    description: Optional[str] = None
    priority: str
    is_completed: bool
    tags: List[str] = []
    source_platform: Optional[str] = None
    linked_problem_id: Optional[int] = None
    order: int
    created_at: datetime
    resolved_at: Optional[datetime] = None
    rating: Optional[int] = None
    url: Optional[str] = None
    already_solved: bool = False

    @staticmethod
    def resolve_rating(obj):
        if obj.linked_problem and obj.linked_problem.platform_metadata:
            return obj.linked_problem.platform_metadata.get('rating')
        return None

    @staticmethod
    def resolve_url(obj):
        if obj.linked_problem:
            return obj.linked_problem.url
        return None

    @staticmethod
    def resolve_tags(obj):
        # Mergear tags do problema (se houver) e as tags manuais
        ptags = []
        if obj.linked_problem and obj.linked_problem.platform_metadata:
            ptags = obj.linked_problem.platform_metadata.get('tags', [])
        
        all_tags = list(ptags) + list(obj.tags)
        # return unique preserving order
        seen = set()
        return [x for x in all_tags if not (x in seen or seen.add(x))]

    @staticmethod
    def resolve_already_solved(obj):
        if obj.linked_problem:
            # Puxamos o tracking vinculado. Para evitar o bug do MVP onde o UserID do QueueItem difere 
            # do UserID gerado pelo ETL (ex: Queue user=8, Tracking user=9), pegamos o first() global da questão.
            tracking = obj.linked_problem.user_trackings.first()
            if tracking:
                success_system = tracking.system_status in ['SOLVED_LIVE', 'UPSOLVED', 'PRACTICE_AC']
                success_review = tracking.review_status in ['DONE', 'TEAM_DONE']
                return success_system or success_review
        return False

class QueueCreateSchema(Schema):
    title: str
    description: Optional[str] = None
    item_type: str = 'PROBLEM'
    priority: str = 'P2'
    source_platform: Optional[str] = None
    linked_problem_id: Optional[int] = None

class QueueUpdatePrioritySchema(Schema):
    priority: str

class QueueUpdateStatusSchema(Schema):
    is_completed: bool

class QueueReorderSchema(Schema):
    ordered_ids: List[int]  # Lista de IDs na nova ordem desejada

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
    user = User.objects.first()
    # Filtra problemas que o usuário marcou como DONE na triagem
    problem_ids = UserProblemTracking.objects.filter(
        user=user, 
        review_status='DONE'
    ).values_list('problem_id', flat=True)
    
    qs = Problem.objects.filter(id__in=problem_ids).select_related('contest')
    
    if platform:
        qs = qs.filter(platform=platform)
        
    return qs

@api.get("/stats", response=StatsSchema)
def get_stats(request):
    user = User.objects.first()
    solved_count = UserProblemTracking.objects.filter(user=user, review_status='DONE').count()
    return {
        "total_solved": solved_count,
        "total_submissions": Submission.objects.count(),
        "total_contests": Contest.objects.count(),
        "platform_breakdown": {
            "cf_solved": UserProblemTracking.objects.filter(
                user=user, 
                review_status='DONE', 
                problem__platform__in=['CF_OFFICIAL', 'CF_GYM']
            ).count(),
            "cses_solved": UserProblemTracking.objects.filter(
                user=user, 
                review_status='DONE', 
                problem__platform='CSES'
            ).count()
        }
    }

# === QUEUE / TRACKING ===

@api.get("/queue", response=List[QueueSchema])
def list_queue(request):
    """Retorna a fila completa, ordenada pela posição manual."""
    return QueueItem.objects.all().order_by('order', '-created_at')

@api.post("/queue", response=QueueSchema)
def create_queue_item(request, payload: QueueCreateSchema):
    """Cria um novo item na fila. Posição = final da fila."""
    user = User.objects.first()  # MVP mono-usuário
    max_order = QueueItem.objects.count()
    item = QueueItem.objects.create(
        user=user,
        title=payload.title,
        description=payload.description,
        item_type=payload.item_type,
        priority=payload.priority,
        source_platform=payload.source_platform,
        linked_problem_id=payload.linked_problem_id,
        order=max_order,
    )
    return item

@api.post("/queue/{item_id}/toggle", response=QueueSchema)
def toggle_queue_done(request, item_id: int):
    """Alterna o estado boolean is_completed de um item da fila."""
    item = QueueItem.objects.get(id=item_id)
    item.is_completed = not item.is_completed
    
    if item.is_completed:
        from django.utils import timezone
        item.resolved_at = timezone.now()
    else:
        item.resolved_at = None
        
    item.save()
    return item

@api.post("/queue/{item_id}/priority", response=QueueSchema)
def update_queue_priority(request, item_id: int, payload: QueueUpdatePrioritySchema):
    item = QueueItem.objects.get(id=item_id)
    item.priority = payload.priority
    item.save()
    return item

@api.post("/queue/reorder")
def reorder_queue(request, payload: QueueReorderSchema):
    """Recebe a lista de IDs na nova ordem e atualiza o campo order."""
    for index, item_id in enumerate(payload.ordered_ids):
        QueueItem.objects.filter(id=item_id).update(order=index)
    return {"ok": True}

@api.post("/queue/{item_id}/status", response=QueueSchema)
def update_queue_status(request, item_id: int, payload: QueueUpdateStatusSchema):
    item = QueueItem.objects.get(id=item_id)
    item.is_completed = payload.is_completed
    
    if item.is_completed:
        from django.utils import timezone
        item.resolved_at = timezone.now()
    else:
        item.resolved_at = None
        
    item.save()
    return item

# --- Edição inline: atualiza campos parciais de um item ---

class QueuePatchSchema(Schema):
    priority: Optional[str] = None
    description: Optional[str] = None

@api.patch("/queue/{item_id}", response=QueueSchema)
def patch_queue_item(request, item_id: int, payload: QueuePatchSchema):
    """Edição parcial de um item da fila (prioridade, descrição)."""
    item = QueueItem.objects.get(id=item_id)
    if payload.priority is not None:
        item.priority = payload.priority
    if payload.description is not None:
        item.description = payload.description
    item.save()
    return item

# --- Busca de problemas no banco para o modal de criação ---

class ProblemSearchSchema(Schema):
    id: int
    platform_id: str
    title: str
    platform: str

@api.get("/problems/search", response=List[ProblemSearchSchema])
def search_problems(request, q: str = "", platform: Optional[str] = None, limit: int = 10):
    """Busca problemas por ID ou título. Usado pelo modal de criação."""
    from django.db.models import Q
    qs = Problem.objects.all()
    if platform:
        if platform == "CODEFORCES":
            qs = qs.filter(platform__in=["CF_OFFICIAL", "CF_GYM"])
        else:
            qs = qs.filter(platform=platform)
    if q:
        qs = qs.filter(Q(platform_id__icontains=q) | Q(title__icontains=q))
    return qs[:limit]