"""Local-only preview utilities. Never imported by production settings."""
from pathlib import Path
import sqlite3

from django.conf import settings
from django.http import JsonResponse


def copy_database(source, target, root):
    source, target, root = (Path(p).resolve() for p in (source, target, root))
    if not target.is_relative_to(root) or target == source:
        raise ValueError('Preview must be a separate file inside the preview directory')
    if target.exists():
        raise ValueError('Preview already exists; choose a new destination')
    if not source.is_file():
        raise ValueError('Source SQLite database does not exist')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental overwrite, including concurrent runs.
    with target.open('xb'):
        pass
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(target) as preview:
            original.backup(preview)


class PreviewNetworkGuard:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'VISUAL_PREVIEW', False) and (
            request.path.startswith('/api/sync/') or request.path.endswith('/predict')
        ):
            return JsonResponse({'detail': 'Prévia local: sincronização e classificação do produto estão desativadas.'}, status=403)
        return self.get_response(request)


def simulated_prediction(problem, model, scenario):
    """Explicit deterministic UI scenarios; no provider, scraping or persistence."""
    from ninja.errors import HttpError
    from .ai_lab.diagnostics import ClassificationFailure
    if scenario not in {'success', 'partial', 'visual', 'error', 'exact', 'overestimate', 'underestimate'}:
        raise HttpError(400, 'Selecione um cenário de simulação local.')
    if scenario == 'error':
        raise ClassificationFailure(502, 'Simulação local: resposta inválida do provedor. Nenhuma previsão foi salva.',
            stage='provider', code='invalid_output', model=model, platform=problem.platform)
    metadata = problem.platform_metadata or {}
    reference = metadata.get('rating')
    anchor = reference if type(reference) is int and 800 <= reference <= 3500 else 1600
    rating = {'exact': anchor, 'overestimate': min(3500, anchor + 200),
              'underestimate': max(800, anchor - 200)}.get(scenario, 1600)
    valid = scenario != 'partial' and rating % 100 == 0
    return {
        'rating': rating if valid else None,
        'tags': ['graphs', 'dfs and similar'],
        'reasoning': 'Simulação local para revisar a interface. Este resultado não foi gerado por IA.',
        'raw_data': None, 'real_rating': metadata.get('rating'),
        'real_tags': metadata.get('tags', []), 'model': model,
        'cached': False, 'rating_status': 'valid' if valid else 'invalid_output',
        'tags_status': 'valid', 'discarded_tags_count': 0,
        'visual_status': 'unprocessed' if scenario == 'visual' else 'text_only',
    }
