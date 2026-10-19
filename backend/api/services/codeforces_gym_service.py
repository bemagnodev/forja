import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from django.utils import timezone
from api.models import Contest, Problem, PlatformChoices
from api.services.codeforces_client import CodeforcesClient, CFResult, CFErrorType
from api.services.problem_metadata import upsert_problem_metadata

logger = logging.getLogger(__name__)


@dataclass
class GymSyncResult:
    """
    Estrutura de resultado da sincronização de metadados e catálogo de um Gym.
    Contém a instância de Contest, contadores precisos e status do erro caso haja falha.
    Implementa __bool__ para permitir verificações idiomáticas 'if result:'.
    """
    contest: Optional[Contest]
    contest_created: bool = False
    problems_created: int = 0
    problems_updated: int = 0
    error_type: CFErrorType = CFErrorType.NONE
    error_message: str = ""

    @property
    def is_success(self) -> bool:
        return self.contest is not None and self.error_type == CFErrorType.NONE

    @property
    def is_permanent_failure(self) -> bool:
        return self.error_type == CFErrorType.PERMANENT

    @property
    def is_transient_failure(self) -> bool:
        return self.error_type == CFErrorType.TRANSIENT

    def __bool__(self) -> bool:
        return self.contest is not None


def ensure_codeforces_gym_metadata(contest_id: str, client: Optional[CodeforcesClient] = None) -> GymSyncResult:
    """
    Garante os metadados e o catálogo de problemas completo de um Codeforces Gym.
    Localiza o contest canônico por (platform, platform_id), cria ou atualiza os metadados existentes,
    e cria ou atualiza o catálogo de problemas retornado pela API oficial do Codeforces.
    Atualiza problemas pela identidade única com merge transacional dos metadados.
    """
    if client is None:
        client = CodeforcesClient(timeout=30)

    try:
        cf_res = client.get_gym_standings_result(str(contest_id))
    except Exception as e:
        logger.exception("Erro ao consultar dados do Gym %s: %s", contest_id, e)
        return GymSyncResult(contest=None, error_type=CFErrorType.TRANSIENT, error_message=str(e))

    if not cf_res.is_success:
        logger.warning("Não foi possível obter dados para o Gym %s (tipo: %s, msg: %s).", contest_id, cf_res.error_type, cf_res.error_message)
        return GymSyncResult(contest=None, error_type=cf_res.error_type, error_message=cf_res.error_message)

    data = cf_res.data
    cf_contest = data.get('contest', {})
    cf_problems = data.get('problems', [])

    name = cf_contest.get('name', f"Gym {contest_id}")
    start_epoch = cf_contest.get('startTimeSeconds')
    duration = cf_contest.get('durationSeconds', 0)

    start_time = None
    if start_epoch:
        start_time = datetime.fromtimestamp(start_epoch, tz=timezone.UTC)

    # Localização determinística para evitar quebras por MultipleObjectsReturned caso haja duplicidades históricas
    existing_contests = Contest.objects.filter(
        platform=PlatformChoices.CF_GYM,
        platform_id=str(contest_id)
    ).order_by('-duration_seconds', '-id')

    contest = existing_contests.first()
    contest_created = False

    if contest:
        contest.name = name
        contest.start_time = start_time
        contest.duration_seconds = duration
        contest.save()
    else:
        contest = Contest.objects.create(
            platform=PlatformChoices.CF_GYM,
            platform_id=str(contest_id),
            name=name,
            start_time=start_time,
            duration_seconds=duration,
        )
        contest_created = True

    problems_created = 0
    problems_updated = 0

    for p in cf_problems:
        index = p.get('index', '')
        problem_id = f"{contest_id}{index}"
        prob_name = p.get('name', '')
        title = f"{index}. {prob_name}" if prob_name else problem_id

        metadata = {
            'rating': p.get('rating'),
            'tags': p.get('tags', []),
        }

        _, created = upsert_problem_metadata(
            platform=PlatformChoices.CF_GYM, platform_id=problem_id,
            fields={"title": title, "contest": contest}, metadata=metadata,
        )
        problems_created += int(created)
        problems_updated += int(not created)

    return GymSyncResult(
        contest=contest,
        contest_created=contest_created,
        problems_created=problems_created,
        problems_updated=problems_updated,
        error_type=CFErrorType.NONE
    )
