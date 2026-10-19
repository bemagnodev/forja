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
from .ai_lab.explore import DEFAULT_MODEL, DEFAULT_PROMPT_VERSION, classify_problem, resolve_model
from .ai_lab.product import PRODUCT_RATING_DOMAIN, validate_product_prediction
from .ai_lab.classification import load_prompt
from .ai_lab.dataset import content_hash
from .ai_lab.contracts import ProviderFailure
from .services.problem_metadata import upsert_problem_metadata
from .services.sync_dispatcher import dispatch_sync

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


# Saved AI Lab experiments: these endpoints never scrape or call a model.
def _ai_lab_read(reader, *args):
    from pathlib import Path
    from django.conf import settings
    from ninja.errors import HttpError

    root = Path(getattr(settings, "AI_LAB_RESULTS_ROOT", settings.BASE_DIR / "var" / "ai_lab"))
    try:
        if not getattr(settings, "AI_LAB_USE_PRIVATE_RESULTS", False):
            from .ai_lab.results import list_snapshots, read_snapshot
            root = Path(getattr(settings, "AI_LAB_PUBLISHED_ROOT", Path(__file__).parent / "ai_lab" / "published"))
            return read_snapshot(root, *args) if args else list_snapshots(root)
        return reader(root, *args)
    except (OSError, ValueError, KeyError, TypeError):
        raise HttpError(503, "Resultados indisponíveis ou incompatíveis") from None
    except LookupError:
        raise HttpError(404, "Benchmark não encontrado") from None


@api.get("/ai-lab/benchmarks", response=dict)
def ai_lab_benchmarks(request):
    from .ai_lab.results import list_benchmarks

    return {"benchmarks": _ai_lab_read(list_benchmarks)}


@api.get("/ai-lab/benchmarks/{benchmark_id}", response=dict)
def ai_lab_benchmark(request, benchmark_id: str):
    from .ai_lab.results import read_benchmark

    return _ai_lab_read(read_benchmark, benchmark_id)

# === AUTH & CONVITES ===
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

class SetPasswordSchema(Schema):
    uid: str
    token: str
    password: str

class AuthResponseSchema(Schema):
    success: bool
    message: str

from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

@api.post("/auth/set-password", response={200: AuthResponseSchema, 400: AuthResponseSchema}, auth=None)
def set_user_password(request, payload: SetPasswordSchema):
    """Permite ao usuário definir/trocar sua senha usando o link de convite seguro gerado pelo admin"""
    try:
        uid = force_str(urlsafe_base64_decode(payload.uid))
    except (TypeError, ValueError, OverflowError):
        return 400, {"success": False, "message": "Link de convite inválido ou expirado."}

    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(pk=uid)
        except User.DoesNotExist:
            return 400, {"success": False, "message": "Link de convite inválido ou expirado."}

        if not default_token_generator.check_token(user, payload.token):
            return 400, {"success": False, "message": "O link de convite expirou ou já foi utilizado."}

        try:
            validate_password(payload.password, user=user)
        except ValidationError as e:
            return 400, {"success": False, "message": " ".join(e.messages)}

        user.set_password(payload.password)
        if not user.is_active:
            user.is_active = True
        user.save()

    return 200, {"success": True, "message": f"Senha de '{user.username}' definida com sucesso!"}

def get_active_user(request):
    """Retorna o usuário ativo (autenticado via JWT)"""
    return request.user

# === USERS ===
class UserProfileSchema(Schema):
    username: str
    first_name: str
    last_name: str
    email: str

@api.get("/users/me", response=UserProfileSchema)
def get_me(request):
    user = get_active_user(request)
    return user

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
    ai_visual_status: Optional[str] = None


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

    @staticmethod
    def resolve_ai_visual_status(obj):
        if obj.linked_problem and obj.linked_problem.platform_metadata:
            return obj.linked_problem.platform_metadata.get('ai_visual_status')
        return None


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
    model: Optional[str] = None
    cached: bool = False
    rating_status: Optional[str] = None
    tags_status: Optional[str] = None
    discarded_tags_count: int = 0
    visual_status: Optional[str] = None
    prompt_version: Optional[str] = None
    prompt_hash: Optional[str] = None
    rating_domain: Optional[str] = None

def _classify_for_ui(problem, selected_model):
    """Shared external I/O only; callers decide whether anything is persisted."""
    from requests.exceptions import RequestException
    from ninja.errors import HttpError

    # Scraper selection
    from .services.scrapers import CodeforcesScraper, AtCoderScraper, CSESScraper
    
    if problem.platform in ["CF_OFFICIAL", "CF_GYM"]:
        scraper = CodeforcesScraper()
    elif problem.platform == "ATCODER":
        scraper = AtCoderScraper()
    elif problem.platform == "CSES":
        scraper = CSESScraper()
    else:
        raise HttpError(400, "Plataforma não suportada para classificação")

    try:
        problem_data = scraper.scrape(problem.url)
    except UnparseableProblemException:
        raise HttpError(400, "Não foi possível extrair o enunciado dessa questão") from None
    except RequestException:
        raise HttpError(502, "Erro de conexão ao obter o enunciado") from None
        
    # AI Classifier
    try:
        ai_result = classify_problem(problem_data, model_name=selected_model)
    except ProviderFailure as exc:
        status, message = {
            "rate_limit": (429, "Limite do modelo atingido. Aguarde a renovação da cota; nenhuma repetição foi feita."),
            "authentication": (503, "Chave ou acesso do provedor indisponível. Confira a configuração do backend."),
            "invalid_output": (502, "O modelo retornou rating ou tags fora do contrato. Nenhuma previsão foi salva."),
            "parsing": (502, "O modelo retornou uma resposta incompleta ou inválida."),
            "timeout": (504, "O provedor não respondeu a tempo. Nenhuma repetição automática foi feita."),
        }.get(exc.category, (503, "O provedor está indisponível para essa classificação."))
        if exc.http_status is not None:
            message += f" Provedor: HTTP {exc.http_status} ({exc.category})."
        raise HttpError(status, message) from None
    except ValueError as exc:
        raise HttpError(400, str(exc)) from None
    except Exception:
        raise HttpError(503, "Não foi possível concluir a classificação. Confira a configuração do provedor.") from None
    return ai_result, problem_data


def _prediction_response(ai_result, metadata, selected_model, problem_data=None, cached=False):
    return {
        "rating": ai_result.get("predicted_rating"),
        "tags": ai_result.get("predicted_tags", []),
        "reasoning": ai_result.get("reasoning", ""),
        "raw_data": problem_data,
        "real_rating": metadata.get("rating"),
        "real_tags": metadata.get("tags", []),
        "model": selected_model, "cached": cached,
        "rating_status": ai_result.get("rating_status"),
        "tags_status": ai_result.get("tags_status"),
        "discarded_tags_count": ai_result.get("discarded_tags_count", 0),
        "visual_status": ai_result.get("visual_status"),
        "prompt_version": ai_result.get("prompt_version"),
        "prompt_hash": ai_result.get("prompt_hash"),
        "rating_domain": ai_result.get("rating_domain"),
    }


@api.post("/ai-lab/problems/{problem_id}/classify", response=AIPredictionSchema)
def explore_problem(request, problem_id: int, model_name: Optional[str] = None):
    from django.shortcuts import get_object_or_404
    from ninja.errors import HttpError
    try:
        selected_model = resolve_model(model_name)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from None
    problem = get_object_or_404(Problem, id=problem_id)
    ai_result, problem_data = _classify_for_ui(problem, selected_model)
    return _prediction_response(ai_result, problem.platform_metadata or {}, selected_model, problem_data)


@api.post("/problems/{problem_id}/predict", response=AIPredictionSchema)
def predict_problem(request, problem_id: int, model_name: Optional[str] = None, force: bool = False):
    from django.shortcuts import get_object_or_404
    from ninja.errors import HttpError
    if model_name is not None and model_name != DEFAULT_MODEL:
        raise HttpError(400, "Use o Explorar para testar outros modelos sem alterar a previsão do produto")
    problem = get_object_or_404(Problem, id=problem_id)
    metadata = problem.platform_metadata or {}
    prompt_hash = content_hash(load_prompt(DEFAULT_PROMPT_VERSION))
    cached_prediction = validate_product_prediction({"rating": metadata.get("ai_rating"), "tags": metadata.get("ai_tags")})
    if (not force and metadata.get("ai_model") == DEFAULT_MODEL and metadata.get("ai_prompt_hash") == prompt_hash
            and metadata.get("ai_prompt_version") == DEFAULT_PROMPT_VERSION
            and metadata.get("ai_rating_domain") == PRODUCT_RATING_DOMAIN
            and metadata.get("ai_visual_status") in ("unprocessed", "not_applicable")
            and isinstance(metadata.get("ai_reasoning"), str)
            and cached_prediction["rating_status"] == "valid" and cached_prediction["tags_status"] == "valid"):
        saved = {"predicted_rating": metadata["ai_rating"], "predicted_tags": metadata["ai_tags"], "reasoning": metadata["ai_reasoning"],
                 "rating_status": "valid", "tags_status": "valid", "prompt_hash": prompt_hash, "prompt_version": DEFAULT_PROMPT_VERSION,
                 "rating_domain": PRODUCT_RATING_DOMAIN, "visual_status": metadata["ai_visual_status"]}
        return _prediction_response(saved, metadata, DEFAULT_MODEL, cached=True)

    ai_result, problem_data = _classify_for_ui(problem, DEFAULT_MODEL)
    validated = validate_product_prediction({"rating": ai_result.get("predicted_rating"), "tags": ai_result.get("predicted_tags")})
    if (validated["rating_status"] != "valid" or validated["tags_status"] != "valid"
            or ai_result.get("rating_status", "valid") != "valid" or ai_result.get("tags_status", "valid") != "valid"):
        raise HttpError(502, "Resposta parcial ou inválida: a previsão salva do produto foi preservada")
    # Acquire the row lock only after scraping/inference; merge the latest metadata.
    current, _ = upsert_problem_metadata(platform=problem.platform, platform_id=problem.platform_id, metadata={
        "ai_rating": validated["rating"], "ai_tags": ai_result["predicted_tags"], "ai_reasoning": ai_result.get("reasoning", ""),
        "ai_model": DEFAULT_MODEL, "ai_prompt_hash": ai_result.get("prompt_hash", prompt_hash),
        "ai_prompt_version": ai_result.get("prompt_version", DEFAULT_PROMPT_VERSION),
        "ai_rating_domain": PRODUCT_RATING_DOMAIN,
        "ai_visual_status": ai_result.get("visual_status", "not_applicable"),
    })
    return _prediction_response(ai_result, current.platform_metadata, DEFAULT_MODEL, problem_data)


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
    url: Optional[str] = None

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

    dispatch_sync("sync_cf", user.cf_handle)

    return {
        "success": True,
        "message": "Sincronização iniciada. Os dados serão atualizados em instantes.",
        "handle": user.cf_handle,
        "changes": 0,
    }

@api.post("/sync/atcoder", response=SyncResultSchema)
def sync_atcoder(request):
    """Dispara o sync incremental do AtCoder para o usuário configurado."""
    user = get_active_user(request)
    if not user.atcoder_handle:
        return {"success": False, "message": "Nenhum handle configurado.", "handle": "", "changes": 0}

    dispatch_sync("sync_atcoder", user.atcoder_handle)

    return {
        "success": True,
        "message": "Sincronização iniciada. Os dados serão atualizados em instantes.",
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
    ai_visual_status: Optional[str] = None
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
    def resolve_ai_visual_status(obj):
        return obj.platform_metadata.get('ai_visual_status') if obj.platform_metadata else None

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

    from django.db.models import F, Value
    from django.db.models.functions import Concat
    from .models import PlatformChoices

    participations = list(
        ContestParticipation.objects
        .select_related('contest')
        .filter(user=user)
        .annotate(provisional_name=Concat(Value('Gym '), F('contest__platform_id')))
        .exclude(contest__platform=PlatformChoices.CF_GYM, contest__name=F('provisional_name'))
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
