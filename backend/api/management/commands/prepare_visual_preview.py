from datetime import timedelta

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.utils import timezone

from api.visual_preview import copy_database


class Command(BaseCommand):
    help = 'Copy real local data into an isolated visual preview, migrate and seed QA cases'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--source-user', type=int, required=True)

    def handle(self, *args, **options):
        if settings.SETTINGS_MODULE != 'core.settings_visual_preview':
            raise CommandError('Use --settings=core.settings_visual_preview')
        try:
            copy_database(settings.BASE_DIR / 'db.sqlite3', settings.DATABASES['default']['NAME'], settings.VISUAL_PREVIEW_ROOT)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        call_command('migrate', interactive=False, verbosity=0)
        from api.models import User
        with transaction.atomic():
            # Only the COPY is changed. Existing history/relations remain intact.
            user = User.objects.get(pk=options['source_user'])
            user.username = 'preview_real'
            user.email = ''
            user.cses_token = None
            user.set_password('ForjaLocal2026!')
            user.save()
            seed_qa_cases()
        self.stdout.write(self.style.SUCCESS('Prévia criada. Contas: preview_real, preview_qa e preview_empty. Senha LOCAL: ForjaLocal2026!'))


@transaction.atomic
def seed_qa_cases():
    if not getattr(settings, 'VISUAL_PREVIEW', False):
        raise ValueError('Synthetic cases require explicit preview settings')
    from api.models import User, Contest, Problem, ContestParticipation, Submission, UserProblemTracking, QueueItem
    qa = User.objects.create_user(username='preview_qa', password='ForjaLocal2026!')
    now = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
    contest = Contest.objects.create(platform='CF_GYM', platform_id='999900',
        name='Treino local — título longo, resultados parciais e escolha de upsolving', start_time=now - timedelta(days=2), duration_seconds=18000)
    ContestParticipation.objects.create(user=qa, contest=contest, is_virtual=True,
        participation_date=now - timedelta(days=2), session_start_time=now - timedelta(days=2),
        results_synced_at=now, solve_count=4, upsolve_count=3, total_problems=15, rank=12, rank_context='VIRTUAL', penalty=810)
    for i in range(15):
        index = chr(65 + i)
        metadata = {'index': index}
        if i % 3 == 0:
            metadata.update(rating=1000 + i * 100, tags=['math', 'implementation', 'greedy'])
        elif i % 3 == 1:
            metadata.update(ai_rating=1500 + i * 100, ai_tags=['graphs', 'dp', 'trees'])
        problem = Problem.objects.create(contest=contest, platform='CF_GYM', platform_id=f'999900{index}',
            title=f'{index}. Questão local {index} com um título longo para verificar a leitura', platform_metadata=metadata)
        status = 'SOLVED_LIVE' if i < 4 else 'UPSOLVED' if i < 6 else 'PENDING_UPSOLVE' if i < 9 else 'UNATTEMPTED'
        UserProblemTracking.objects.create(user=qa, problem=problem, system_status=status,
            review_status='DONE' if i < 6 or i == 14 else 'DOABLE' if i < 9 else 'PENDING_TRIAGE')
        if i < 9 and i not in (0, 2):
            Submission.objects.create(user=qa, problem=problem, platform_submission_id=f'preview-{i}-wa',
                participant_type='VIRTUAL', verdict='WRONG_ANSWER', creation_time=now-timedelta(days=2)+timedelta(minutes=10+i),
                relative_time_seconds=600+i*60, session_start_time=now-timedelta(days=2))
        if i < 6:
            Submission.objects.create(user=qa, problem=problem, platform_submission_id=f'preview-{i}-ac',
                participant_type='VIRTUAL' if i < 4 else 'PRACTICE', verdict='OK',
                creation_time=now-timedelta(days=2 if i < 4 else 1)+timedelta(minutes=30+i*15),
                relative_time_seconds=(30+i*15)*60 if i < 4 else None,
                session_start_time=now-timedelta(days=2) if i < 4 else None)
        QueueItem.objects.create(user=qa, linked_problem=problem, title=problem.title, item_type='PROBLEM',
            priority=['P0', 'P1', 'P2', 'UPSOLVING', 'FUTURE'][i % 5], source_platform='CF_GYM',
            description='Cenário sintético local para conferir títulos, metadados e ações.', order=i)
    QueueItem.objects.create(user=qa, title='Revisar árvores — sessão sem problema vinculado', item_type='STUDY_SESSION', priority='P1')
    User.objects.create_user(username='preview_empty', password='ForjaLocal2026!')
    Submission.objects.create(user=qa, problem=Problem.objects.get(platform_id='999900A', platform='CF_GYM'),
        platform_submission_id='preview-after-ac', participant_type='VIRTUAL', verdict='WRONG_ANSWER',
        creation_time=now-timedelta(days=2)+timedelta(minutes=90), relative_time_seconds=5400, session_start_time=now-timedelta(days=2))
    for index, verdict in [('B', 'TIME_LIMIT_EXCEEDED'), ('C', 'COMPILATION_ERROR')]:
        Submission.objects.create(user=qa, problem=Problem.objects.get(platform_id=f'999900{index}', platform='CF_GYM'),
            platform_submission_id=f'preview-extra-{index}', participant_type='VIRTUAL', verdict=verdict,
            creation_time=now-timedelta(days=2)+timedelta(minutes=20), relative_time_seconds=1200, session_start_time=now-timedelta(days=2))
    for i, rank in enumerate([None, 7, 3]):
        start = now - timedelta(days=3+i)
        other = Contest.objects.create(platform='CF_OFFICIAL', platform_id=str(999901+i),
            name=f'Treino local {i+1} — histórico parcial', start_time=start, duration_seconds=7200)
        ContestParticipation.objects.create(user=qa, contest=other, participation_date=start,
            is_virtual=False, rank=rank, rank_context='OFFICIAL' if rank else '', total_problems=1)
        Problem.objects.create(platform='CF_OFFICIAL', platform_id=f'{999901+i}A', contest=other,
            title='A. Metadados ainda não confirmados', platform_metadata={'index': 'A'})
