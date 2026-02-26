from ninja import NinjaAPI, Schema
from typing import List, Optional
from datetime import datetime
from django.db.models import Count
from .models import Submission, Problem, Contest

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