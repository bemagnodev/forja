"""
Comando de management: clone_demo_user (v2 - Bulk Insert Otimizado)

Usa bulk_create com ignore_conflicts=True e chunking para ser
ordens de magnitude mais rápido que get_or_create em loop.

Estratégia:
- ContestParticipation: bulk_create em chunks de 500
- Submission: bulk_create em chunks de 500 com IDs prefixados "demo_"
- UserProblemTracking: bulk_create em chunks de 500

Uso:
    python manage.py clone_demo_user --source membro1 --source membro2 --source membro3
"""
from django.core.management.base import BaseCommand
from api.models import (
    User, Submission, UserProblemTracking, ContestParticipation
)

CHUNK_SIZE = 500


def bulk_insert_chunks(model, objects, unique_fields, stdout):
    """
    Insere objetos em chunks, ignorando conflitos de chave única.
    Retorna o total de objetos enviados (não necessariamente inseridos).
    """
    total = len(objects)
    inserted = 0
    for i in range(0, total, CHUNK_SIZE):
        chunk = objects[i: i + CHUNK_SIZE]
        # ignore_conflicts=True: silencia IntegrityError em duplicatas
        model.objects.bulk_create(chunk, ignore_conflicts=True)
        inserted += len(chunk)
        stdout.write(f'    {inserted}/{total}...')
    return total


class Command(BaseCommand):
    help = 'Clona dados de usuários-fonte para o forja_demo via bulk_create otimizado.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            action='append',
            dest='sources',
            required=True,
            help='Username do usuário-fonte. Pode ser repetido.'
        )
        parser.add_argument(
            '--target',
            type=str,
            default='forja_demo',
            help='Username do usuário-alvo (padrão: forja_demo).'
        )

    def handle(self, *args, **kwargs):
        source_usernames = kwargs['sources']
        target_username = kwargs['target']

        try:
            target_user = User.objects.get(username=target_username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Usuário-alvo "{target_username}" não encontrado.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'[Bulk Clone] Iniciando para "{target_user.username}"...'
        ))

        # Pré-carrega IDs já existentes para o alvo (evita re-inserir o que já foi clonado)
        existing_part_contest_ids = set(
            ContestParticipation.objects.filter(user=target_user).values_list('contest_id', flat=True)
        )
        existing_sub_ids = set(
            Submission.objects.filter(user=target_user).values_list('platform_submission_id', flat=True)
        )
        existing_tracking_problem_ids = set(
            UserProblemTracking.objects.filter(user=target_user).values_list('problem_id', flat=True)
        )
        self.stdout.write(f'  Ja existem: {len(existing_part_contest_ids)} participacoes | {len(existing_sub_ids)} subs | {len(existing_tracking_problem_ids)} trackings')

        total_parts = 0
        total_subs = 0
        total_trackings = 0

        for source_username in source_usernames:
            try:
                source_user = User.objects.get(username=source_username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Fonte "{source_username}" nao encontrada. Pulando.'))
                continue

            self.stdout.write(f'\n--- Processando fonte: "{source_user.username}" ---')

            # --- 1. ContestParticipation ---
            self.stdout.write('  > ContestParticipations...')
            src_parts = ContestParticipation.objects.filter(user=source_user).select_related('contest')
            new_parts = [
                ContestParticipation(
                    user=target_user,
                    contest=p.contest,
                    is_virtual=p.is_virtual,
                    participation_date=p.participation_date,
                    solve_count=p.solve_count,
                    upsolve_count=p.upsolve_count,
                    total_problems=p.total_problems,
                    rank=p.rank,
                )
                for p in src_parts
                if p.contest_id not in existing_part_contest_ids
            ]
            if new_parts:
                bulk_insert_chunks(ContestParticipation, new_parts, ['user', 'contest'], self.stdout)
                # Atualiza cache local para evitar duplicatas entre fontes
                existing_part_contest_ids.update(p.contest.id for p in src_parts)
            total_parts += len(new_parts)
            self.stdout.write(self.style.SUCCESS(f'  [OK] {len(new_parts)} novas participacoes'))

            # --- 2. Submission ---
            self.stdout.write('  > Submissions...')
            src_subs = Submission.objects.filter(user=source_user).select_related('problem')
            new_subs = []
            for s in src_subs:
                demo_id = f"demo_{s.platform_submission_id}"
                if demo_id not in existing_sub_ids:
                    new_subs.append(Submission(
                        platform_submission_id=demo_id,
                        problem=s.problem,
                        user=target_user,
                        participant_type=s.participant_type,
                        verdict=s.verdict,
                        creation_time=s.creation_time,
                    ))
                    existing_sub_ids.add(demo_id)
            if new_subs:
                bulk_insert_chunks(Submission, new_subs, ['platform_submission_id'], self.stdout)
            total_subs += len(new_subs)
            self.stdout.write(self.style.SUCCESS(f'  [OK] {len(new_subs)} novas submissoes'))

            # --- 3. UserProblemTracking ---
            self.stdout.write('  > UserProblemTrackings...')
            src_trackings = UserProblemTracking.objects.filter(user=source_user).select_related('problem')
            new_trackings = []
            for t in src_trackings:
                if t.problem_id not in existing_tracking_problem_ids:
                    # Bypass do save() customizado (FSM) via bulk_create direto
                    # Os estados já foram calculados pela FSM quando o source_user foi sincronizado
                    new_trackings.append(UserProblemTracking(
                        user=target_user,
                        problem=t.problem,
                        system_status=t.system_status,
                        review_status=t.review_status,
                    ))
                    existing_tracking_problem_ids.add(t.problem_id)
            if new_trackings:
                bulk_insert_chunks(UserProblemTracking, new_trackings, ['user', 'problem'], self.stdout)
            total_trackings += len(new_trackings)
            self.stdout.write(self.style.SUCCESS(f'  [OK] {len(new_trackings)} novos trackings'))

        # Copia watermarks de sync do último source
        last_source = User.objects.get(username=source_usernames[-1])
        if last_source.cf_last_sync_time:
            target_user.cf_last_sync_time = last_source.cf_last_sync_time
        if last_source.atcoder_last_sync_time:
            target_user.atcoder_last_sync_time = last_source.atcoder_last_sync_time
        target_user.save()

        self.stdout.write(self.style.SUCCESS(
            f'\n=== Clone Concluido para "{target_user.username}" ===\n'
            f'  ContestParticipations: {total_parts}\n'
            f'  Submissions:           {total_subs}\n'
            f'  UserProblemTrackings:  {total_trackings}\n'
        ))
