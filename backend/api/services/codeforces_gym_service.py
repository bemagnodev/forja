import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from django.utils import timezone
from api.models import Contest, Problem, PlatformChoices
from api.services.codeforces_client import CodeforcesClient

logger = logging.getLogger(__name__)


@dataclass
class GymSyncResult:
    """
    Estrutura de resultado da sincronização de metadados e catálogo de um Gym.
    Contém a instância de Contest e contadores precisos de criação e atualização.
    Implementa __bool__ para permitir verificações idiomáticas 'if result:'.
    """
    contest: Optional[Contest]
    contest_created: bool = False
    problems_created: int = 0
    problems_updated: int = 0

    def __bool__(self) -> bool:
        return self.contest is not None


def ensure_codeforces_gym_metadata(contest_id: str, client: Optional[CodeforcesClient] = None) -> Optional[GymSyncResult]:
    """
    Garante os metadados e o catálogo de problemas completo de um Codeforces Gym.
    Localiza o contest por (platform, platform_id), cria ou atualiza os metadados existentes,
    e cria ou atualiza o catálogo de problemas retornado pela API oficial do Codeforces.
    Retorna GymSyncResult com métricas confiáveis ou None em caso de falha de obtenção.
    """
    if client is None:
        client = CodeforcesClient(timeout=30)

    try:
        data = client.get_gym_standings(str(contest_id))
    except Exception as e:
        logger.exception("Erro ao consultar dados do Gym %s: %s", contest_id, e)
        return None

    if not data:
        logger.warning("Não foi possível obter dados para o Gym %s (pode ser privado ou inexistente).", contest_id)
        return None

    cf_contest = data.get('contest', {})
    cf_problems = data.get('problems', [])

    name = cf_contest.get('name', f"Gym {contest_id}")
    start_epoch = cf_contest.get('startTimeSeconds')
    duration = cf_contest.get('durationSeconds', 0)

    start_time = None
    if start_epoch:
        start_time = datetime.fromtimestamp(start_epoch, tz=timezone.UTC)

    contest, contest_created = Contest.objects.update_or_create(
        platform=PlatformChoices.CF_GYM,
        platform_id=str(contest_id),
        defaults={
            'name': name,
            'start_time': start_time,
            'duration_seconds': duration,
        }
    )

    problems_created = 0
    problems_updated = 0

    for p in cf_problems:
        index = p.get('index', '')
        problem_id = f"{contest_id}{index}"
        prob_name = p.get('name', '')
        title = f"{index}. {prob_name}" if prob_name else problem_id

        _, p_created = Problem.objects.update_or_create(
            platform=PlatformChoices.CF_GYM,
            platform_id=problem_id,
            defaults={
                'title': title,
                'contest': contest,
                'platform_metadata': {
                    'rating': p.get('rating'),
                    'tags': p.get('tags', []),
                }
            }
        )
        if p_created:
            problems_created += 1
        else:
            problems_updated += 1

    return GymSyncResult(
        contest=contest,
        contest_created=contest_created,
        problems_created=problems_created,
        problems_updated=problems_updated,
    )
