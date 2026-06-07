import re
from io import StringIO
from ninja import NinjaAPI, Schema
from typing import List, Optional
from datetime import datetime
from django.db.models import Count
from django.core.management import call_command
from .models import Submission, Problem, Contest, QueueItem, User, UserProblemTracking, ContestParticipation
from .services.scrapers.codeforces import CodeforcesScraper
from .services.scrapers.exceptions import UnparseableProblemException
from .services.ai_classifier import classify_problem

from ninja_jwt.routers.obtain import obtain_pair_router
from ninja_jwt.authentication import JWTAuth

api = NinjaAPI(
    title="A Forja API",
    description="Backend de dados para análise de performance competitiva+",
    version="1.0.0",
    urls_namespace="api",
    auth=JWTAuth(),
)

api.add_router("/token", obtain_pair_router, auth=None)

def get_active_user(request):
    """Retorna o usuário ativo (autenticado via JWT)"""
    return request.user

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
        tracking_list = getattr(obj, '_trackings_list', [])
        return tracking_list[0] if tracking_list else None

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
    platform_id: Optional[str] = None
    # Título real do problema (diferente do title do QueueItem, que pode ser um nome livre)
    problem_title: Optional[str] = None
    # Nome do contest ao qual o problema pertence
    contest_name: Optional[str] = None
    ai_rating: Optional[int] = None
    ai_tags: List[str] = []


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
            # Busca o tracking injetado via prefetch (_trackings_list)
            tracking_list = getattr(obj.linked_problem, '_trackings_list', [])
            tracking = tracking_list[0] if tracking_list else None
            # Fallback
            if not tracking:
                tracking = getattr(obj.linked_problem, '_tracking', None)
            if tracking:
                success_system = tracking.system_status in ['SOLVED_LIVE', 'UPSOLVED', 'PRACTICE_AC']
                success_review = tracking.review_status in ['DONE', 'TEAM_DONE']
                return success_system or success_review
        return False

    @staticmethod
    def resolve_platform_id(obj):
        if obj.linked_problem:
            return obj.linked_problem.platform_id
        return None

    @staticmethod
    def resolve_problem_title(obj):
        # Retorna o título real do Problem.title (não o fallback platform_id)
        if obj.linked_problem:
            return obj.linked_problem.title
        return None

    @staticmethod
    def resolve_contest_name(obj):
        # Retorna o nome do contest ao qual o problema pertence
        if obj.linked_problem and obj.linked_problem.contest:
            return obj.linked_problem.contest.name
        return None

    @staticmethod
    def resolve_ai_rating(obj):
        if obj.linked_problem and obj.linked_problem.platform_metadata:
            return obj.linked_problem.platform_metadata.get('ai_rating')
        return None

    @staticmethod
    def resolve_ai_tags(obj):
        if obj.linked_problem and obj.linked_problem.platform_metadata:
            return obj.linked_problem.platform_metadata.get('ai_tags', [])
        return []


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
    user = get_active_user(request)
    from django.db.models import Prefetch
    qs = Submission.objects.filter(user=user).select_related('problem', 'problem__contest').prefetch_related(
        Prefetch(
            'problem__user_trackings',
            queryset=UserProblemTracking.objects.filter(user=user),
            to_attr='_trackings_list'
        )
    ).order_by('-creation_time')
    
    if platform:
        qs = qs.filter(problem__contest__platform=platform)
    
    return qs[offset : offset + limit]

@api.get("/problems/solved", response=List[ProblemSchema])
def list_solved_problems(request, platform: Optional[str] = None):
    user = get_active_user(request)
    problem_ids = UserProblemTracking.objects.filter(
        user=user, 
        review_status='DONE'
    ).values_list('problem_id', flat=True)
    
    from django.db.models import Prefetch
    qs = Problem.objects.filter(id__in=problem_ids).select_related('contest').prefetch_related(
        Prefetch(
            'user_trackings',
            queryset=UserProblemTracking.objects.filter(user=user),
            to_attr='_trackings_list'
        )
    )
    
    if platform:
        qs = qs.filter(platform=platform)
        
    return qs

class AIPredictionSchema(Schema):
    rating: Optional[int]
    tags: List[str]
    reasoning: str
    raw_data: Optional[dict] = None
    real_rating: Optional[int] = None
    real_tags: List[str] = []

@api.post("/problems/{problem_id}/predict", response=AIPredictionSchema)
def predict_problem(request, problem_id: int, model_name: Optional[str] = None, force: bool = False):
    problem = Problem.objects.get(id=problem_id)
    metadata = problem.platform_metadata or {}
    
    # Cache hit
    if not force and "ai_rating" in metadata and "ai_tags" in metadata and "ai_reasoning" in metadata:
        return {
            "rating": metadata.get("ai_rating"),
            "tags": metadata.get("ai_tags"),
            "reasoning": metadata.get("ai_reasoning"),
            "raw_data": None,
            "real_rating": metadata.get("rating"),
            "real_tags": metadata.get("tags", [])
        }
    
    # Scraper selection
    from .services.scrapers import CodeforcesScraper, AtCoderScraper, CSESScraper
    
    if problem.platform in ["CF_OFFICIAL", "CF_GYM"]:
        scraper = CodeforcesScraper()
    elif problem.platform == "ATCODER":
        scraper = AtCoderScraper()
    elif problem.platform == "CSES":
        scraper = CSESScraper()
    else:
        return 400, {"message": f"Platform {problem.platform} not supported for prediction"}

    try:
        problem_data = scraper.scrape(problem.url)
    except UnparseableProblemException as e:
        return 400, {"message": str(e)}
        
    # AI Classifier
    ai_result = classify_problem(problem_data, model_name=model_name)
    
    # Update DB
    metadata["ai_rating"] = ai_result.get("predicted_rating")
    metadata["ai_tags"] = ai_result.get("predicted_tags", [])
    metadata["ai_reasoning"] = ai_result.get("reasoning", "")
    problem.platform_metadata = metadata
    problem.save()
    
    return {
        "rating": metadata["ai_rating"],
        "tags": metadata["ai_tags"],
        "reasoning": metadata["ai_reasoning"],
        "raw_data": problem_data,
        "real_rating": metadata.get("rating"),
        "real_tags": metadata.get("tags", [])
    }


@api.get("/stats", response=StatsSchema)
def get_stats(request):
    user = get_active_user(request)
    solved_count = UserProblemTracking.objects.filter(user=user, review_status='DONE').count()
    return {
        "total_solved": solved_count,
        "total_submissions": Submission.objects.filter(user=user).count(),
        "total_contests": ContestParticipation.objects.filter(user=user).count(),
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

# === DASHBOARD ===

class TopicStatsSchema(Schema):
    name: str
    solved: int
    accuracy: float

class DashboardKPIsSchema(Schema):
    total_solved: int
    streak: int
    max_streak: int
    acceptance_rate: float
    solved_this_month: int

class DashboardHeatmapSchema(Schema):
    date: str
    count: int

class Last7DaysSchema(Schema):
    activity: List[bool]
    total_solved: int
    average_difficulty: int
    top_topics: List[dict]

class DashboardRecentContestSchema(Schema):
    id: int
    contest_id: int
    name: str
    platform: str
    date: Optional[str]
    progress: dict

class DashboardRecentACSchema(Schema):
    id: int
    problem_name: str
    platform: str
    tags: List[str]
    date: str

class DashboardStatsSchema(Schema):
    kpis: DashboardKPIsSchema
    heatmap: List[DashboardHeatmapSchema]
    last_7_days: Last7DaysSchema
    difficulty_breakdown: dict
    topics: List[TopicStatsSchema]
    recent_contests: List[DashboardRecentContestSchema]
    recent_acs: List[DashboardRecentACSchema]

@api.get("/dashboard/stats", response=DashboardStatsSchema)
def get_dashboard_stats_endpoint(request):
    """Retorna todas as estatísticas agregadas para o painel principal."""
    user = get_active_user(request)
    from .services.dashboard_service import get_dashboard_stats
    return get_dashboard_stats(user)

# === QUEUE / TRACKING ===

@api.get("/queue", response=List[QueueSchema])
def list_queue(request):
    """Retorna a fila completa, ordenada pela posição manual."""
    user = get_active_user(request)
    from django.db.models import Prefetch
    return (
        QueueItem.objects
        .filter(user=user)
        .select_related('linked_problem', 'linked_problem__contest')
        .prefetch_related(
            Prefetch(
                'linked_problem__user_trackings',
                queryset=UserProblemTracking.objects.filter(user=user),
                to_attr='_trackings_list'
            )
        )
        .order_by('order', '-created_at')
    )

@api.post("/queue", response=QueueSchema)
def create_queue_item(request, payload: QueueCreateSchema):
    """Cria um novo item na fila. Posição = final da fila."""
    user = get_active_user(request)
    max_order = QueueItem.objects.filter(user=user).count()
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
    item = QueueItem.objects.get(id=item_id, user=request.user)
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
    item = QueueItem.objects.get(id=item_id, user=request.user)
    item.priority = payload.priority
    item.save()
    return item

@api.post("/queue/reorder")
def reorder_queue(request, payload: QueueReorderSchema):
    """Recebe a lista de IDs na nova ordem e atualiza o campo order."""
    for index, item_id in enumerate(payload.ordered_ids):
        QueueItem.objects.filter(id=item_id, user=request.user).update(order=index)
    return {"ok": True}

@api.post("/queue/{item_id}/status", response=QueueSchema)
def update_queue_status(request, item_id: int, payload: QueueUpdateStatusSchema):
    item = QueueItem.objects.get(id=item_id, user=request.user)
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
    item = QueueItem.objects.get(id=item_id, user=request.user)
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


# === SYNC ===

class SyncResultSchema(Schema):
    success: bool
    message: str
    handle: str
    changes: int

@api.post("/sync/cf", response=SyncResultSchema)
def sync_codeforces(request):
    """Dispara o sync incremental do Codeforces para o usuário configurado."""
    user = get_active_user(request)
    if not user.cf_handle:
        return {"success": False, "message": "Nenhum handle configurado.", "handle": "", "changes": 0}

    import threading
    from django.core.management import call_command
    
    def run_sync():
        try:
            call_command('sync_cf', handle=user.cf_handle)
        except Exception as e:
            print(f"Erro no sync_cf em background: {e}")

    threading.Thread(target=run_sync).start()

    return {
        "success": True,
        "message": "Sincronização iniciada em segundo plano. Os dados aparecerão em breve.",
        "handle": user.cf_handle,
        "changes": 0,
    }

@api.post("/sync/atcoder", response=SyncResultSchema)
def sync_atcoder(request):
    """Dispara o sync incremental do AtCoder para o usuário configurado."""
    user = get_active_user(request)
    if not user.atcoder_handle:
        return {"success": False, "message": "Nenhum handle configurado.", "handle": "", "changes": 0}

    import threading
    from django.core.management import call_command
    
    def run_sync():
        try:
            call_command('sync_atcoder', handle=user.atcoder_handle)
        except Exception as e:
            print(f"Erro no sync_atcoder em background: {e}")

    threading.Thread(target=run_sync).start()

    return {
        "success": True,
        "message": "Sincronização iniciada em segundo plano. Os dados aparecerão em breve.",
        "handle": user.atcoder_handle,
        "changes": 0,
    }

# === UPSOLVING ===

from django.db.models import Case, When, IntegerField, Prefetch

class ContestProgressSchema(Schema):
    solved_live: int
    pending_upsolve: int
    upsolved: int
    unattempted: int
    total: int

class ContestParticipationSchema(Schema):
    id: int
    contest_id: int
    contest_name: str
    contest_platform: str
    participation_date: Optional[datetime]
    is_virtual: bool
    has_debt: bool
    progress: ContestProgressSchema
    url: Optional[str] = None
    rank: Optional[int] = None
    solve_count: int = 0
    upsolve_count: int = 0
    total_problems: int = 0

    @staticmethod
    def resolve_url(obj):
        platform = obj.contest.platform
        pid = obj.contest.platform_id
        if platform == 'CF_OFFICIAL':
            return f"https://codeforces.com/contest/{pid}"
        elif platform == 'CF_GYM':
            return f"https://codeforces.com/gym/{pid}"
        elif platform == 'ATCODER':
            return f"https://atcoder.jp/contests/{pid}"
        return None

    @staticmethod
    def resolve_contest_id(obj):
        return obj.contest.id

    @staticmethod
    def resolve_contest_name(obj):
        return obj.contest.name

    @staticmethod
    def resolve_contest_platform(obj):
        return obj.contest.platform

    @staticmethod
    def resolve_has_debt(obj):
        # Calculado via anotação injetada pela view
        return getattr(obj, '_pending_count', 0) > 0

    @staticmethod
    def resolve_progress(obj):
        return obj._progress if hasattr(obj, '_progress') else {
            'solved_live': 0, 'pending_upsolve': 0,
            'upsolved': 0, 'unattempted': 0, 'total': 0
        }

class ContestProblemSchema(Schema):
    id: int
    platform_id: str
    title: str
    index: str
    rating: Optional[int] = None
    ai_rating: Optional[int] = None
    tags: List[str] = []
    ai_tags: List[str] = []
    url: Optional[str] = None
    system_status: str
    review_status: str
    tracking_id: Optional[int] = None

    @staticmethod
    def resolve_index(obj):
        # Index é a(s) letra(s) no final do platform_id (ex: "100123A" → "A")
        import re
        m = re.search(r'([A-Z]+\d*)$', obj.platform_id)
        return m.group(1) if m else obj.platform_id

    @staticmethod
    def resolve_rating(obj):
        return obj.platform_metadata.get('rating') if obj.platform_metadata else None

    @staticmethod
    def resolve_ai_rating(obj):
        return obj.platform_metadata.get('ai_rating') if obj.platform_metadata else None

    @staticmethod
    def resolve_tags(obj):
        return obj.platform_metadata.get('tags', []) if obj.platform_metadata else []

    @staticmethod
    def resolve_ai_tags(obj):
        return obj.platform_metadata.get('ai_tags', []) if obj.platform_metadata else []

    @staticmethod
    def resolve_url(obj):
        return obj.url

    @staticmethod
    def resolve_system_status(obj):
        tracking = getattr(obj, '_tracking', None)
        return tracking.system_status if tracking else 'UNATTEMPTED'

    @staticmethod
    def resolve_review_status(obj):
        tracking = getattr(obj, '_tracking', None)
        return tracking.review_status if tracking else 'PENDING_TRIAGE'

    @staticmethod
    def resolve_tracking_id(obj):
        tracking = getattr(obj, '_tracking', None)
        return tracking.id if tracking else None

@api.get("/contests", response=List[ContestParticipationSchema])
def list_contest_participations(request):
    """Lista todos os contests que o usuário participou, com progresso dinâmico."""
    user = get_active_user(request)

    participations = list(
        ContestParticipation.objects
        .select_related('contest')
        .filter(user=user)
    )

    contest_ids = [p.contest_id for p in participations]

    # Batch Query (Elimina o problema N+1)
    trackings = UserProblemTracking.objects.filter(
        user=user,
        problem__contest_id__in=contest_ids
    ).values('problem__contest_id', 'system_status')

    counts_by_contest = {cid: {'solved_live': 0, 'pending_upsolve': 0, 'upsolved': 0, 'unattempted': 0, 'total': 0} for cid in contest_ids}

    for t in trackings:
        cid = t['problem__contest_id']
        status = t['system_status']
        counts_by_contest[cid]['total'] += 1
        if status == 'SOLVED_LIVE':
            counts_by_contest[cid]['solved_live'] += 1
        elif status == 'PENDING_UPSOLVE':
            counts_by_contest[cid]['pending_upsolve'] += 1
        elif status == 'UPSOLVED':
            counts_by_contest[cid]['upsolved'] += 1
        elif status == 'UNATTEMPTED':
            counts_by_contest[cid]['unattempted'] += 1

    result = []
    for p in participations:
        p._progress = counts_by_contest.get(p.contest_id, {'solved_live': 0, 'pending_upsolve': 0, 'upsolved': 0, 'unattempted': 0, 'total': 0})
        p._pending_count = p._progress['pending_upsolve']
        result.append(p)

    # Ordena: por data desc
    result.sort(key=lambda p: -(p.participation_date.timestamp() if p.participation_date else 0))

    return result

@api.get("/contests/{contest_id}/problems", response=List[ContestProblemSchema])
def list_contest_problems(request, contest_id: int):
    """Retorna todos os problemas de um contest com status de tracking do usuário."""
    user = get_active_user(request)
    from django.db.models import Prefetch

    problems = list(
        Problem.objects
        .filter(contest_id=contest_id)
        .prefetch_related(
            Prefetch(
                'user_trackings',
                queryset=UserProblemTracking.objects.filter(user=user),
                to_attr='_trackings_list'
            )
        )
        .order_by('platform_id')
    )

    # Injeta o tracking como atributo direto para o resolver conseguir acessar
    for prob in problems:
        tracking_list = getattr(prob, '_trackings_list', [])
        prob._tracking = tracking_list[0] if tracking_list else None

    return problems

class TrackingUpdateSchema(Schema):
    review_status: str

@api.patch("/tracking/{problem_id}", response=ContestProblemSchema)
def update_tracking(request, problem_id: int, payload: TrackingUpdateSchema):
    """Atualiza o review_status de um problema. A FSM do modelo executa automaticamente no save()."""
    user = get_active_user(request)
    tracking, _ = UserProblemTracking.objects.get_or_create(
        user=user,
        problem_id=problem_id,
        defaults={
            'system_status': UserProblemTracking.SystemStatus.UNATTEMPTED,
            'review_status': UserProblemTracking.ReviewStatus.PENDING_TRIAGE,
        }
    )
    tracking.review_status = payload.review_status
    tracking.save()  # FSM executa aqui

    # Recarrega o Problem com tracking injetado para serializar a resposta
    prob = Problem.objects.prefetch_related(
        Prefetch(
            'user_trackings',
            queryset=UserProblemTracking.objects.filter(user=user),
            to_attr='_trackings_list'
        )
    ).get(id=problem_id)
    tracking_list = getattr(prob, '_trackings_list', [])
    prob._tracking = tracking_list[0] if tracking_list else None
    return prob
