from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    cf_handle = models.CharField(max_length=255, null=True, blank=True, help_text="Handle do Codeforces")
    atcoder_handle = models.CharField(max_length=255, null=True, blank=True, help_text="Handle do AtCoder")
    cses_token = models.CharField(max_length=255, null=True, blank=True, help_text="Token de sessão para raspagem do CSES")
    
    # Controle de Sincronização Incremental:
    atcoder_last_sync_time = models.BigIntegerField(null=True, blank=True, help_text="Último Epoch Sincronizado do AtCoder")
    cf_last_sync_time = models.BigIntegerField(null=True, blank=True, help_text="Último Epoch Sincronizado do Codeforces")
    
    # Métricas dinâmicas sem colunas físicas:
    @property
    def total_acs(self):
        # TODO: Retornará dinamicamente count() das questões resolvidas.
        # return self.userproblemtracking_set.filter(review_status='DONE').count()
        pass

class Team(models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(User, related_name="teams")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PlatformChoices(models.TextChoices):
    CF_OFFICIAL = 'CF_OFFICIAL', 'Codeforces Oficial'
    CF_GYM = 'CF_GYM', 'Codeforces Gym'
    ATCODER = 'ATCODER', 'AtCoder'
    CSES = 'CSES', 'CSES'

class Contest(models.Model):
    platform = models.CharField(max_length=20, choices=PlatformChoices.choices)
    platform_id = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    start_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"[{self.get_platform_display()}] {self.name}"

class Problem(models.Model):
    platform = models.CharField(max_length=20, choices=PlatformChoices.choices)
    platform_id = models.CharField(max_length=50) # Ex: 1234A, abc300_a
    title = models.CharField(max_length=255)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, null=True, blank=True, related_name='problems')
    platform_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ['platform', 'platform_id']

    def __str__(self):
        return self.title

class ContestParticipation(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='participations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='contest_participations')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name='contest_participations')
    is_virtual = models.BooleanField(default=False)

    def __str__(self):
        participant = self.team.name if self.team else self.user.username
        return f"{participant} in {self.contest.name}"

class Submission(models.Model): 
    class ParticipantType(models.TextChoices):
        CONTESTANT = 'CONTESTANT', 'Competidor'
        VIRTUAL = 'VIRTUAL', 'Virtual'
        PRACTICE = 'PRACTICE', 'Prática Livre'

    platform_submission_id = models.CharField(max_length=50, unique=True)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    co_authors = models.ManyToManyField(User, related_name='co_authored_submissions', blank=True)
    participant_type = models.CharField(max_length=20, choices=ParticipantType.choices)
    verdict = models.CharField(max_length=50)
    creation_time = models.DateTimeField()

    def __str__(self):
        return f"{self.platform_submission_id} - {self.verdict} by {self.user.username}"

class UserProblemTracking(models.Model):
    # system_status: Realidade técnica extraída das APIs
    class SystemStatus(models.TextChoices):
        UNATTEMPTED = 'UNATTEMPTED', 'Não tentada'
        SOLVED_LIVE = 'SOLVED_LIVE', 'AC no Contest'
        PENDING_UPSOLVE = 'PENDING_UPSOLVE', 'Dívida de Upsolving'
        UPSOLVED = 'UPSOLVED', 'Resolvido depois (Upsolving)'
        PRACTICE_WA = 'PRACTICE_WA', 'Erro em Treino Livre'
        PRACTICE_AC = 'PRACTICE_AC', 'AC em Treino Livre'

    # review_status: Ponto de vista do usuário
    class ReviewStatus(models.TextChoices):
        PENDING_TRIAGE = 'PENDING_TRIAGE', 'Pendente de Triagem'
        DOABLE = 'DOABLE', 'Dá pra fazer'
        FUTURE = 'FUTURE', 'Muito avançada (Futuro)'
        DONE = 'DONE', 'Concluído'
        TEAM_DONE = 'TEAM_DONE', 'Feito pelo Time'
        IGNORED = 'IGNORED', 'Ignorada/Lixo'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_trackings')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='user_trackings')
    system_status = models.CharField(max_length=20, choices=SystemStatus.choices, default=SystemStatus.UNATTEMPTED)
    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING_TRIAGE)

    class Meta:
        unique_together = ['user', 'problem']

    def _sync_system_to_review(self, old_instance=None):
        """
        Sincronizar estados de sistema e de revisão manual.
        Aplicar reatividade bidirecional e proteger estados de sucesso contra o sistema.
        """
        is_new = old_instance is None
        
        def _val(x):
            return x.value if hasattr(x, 'value') else str(x)
            
        system_status_changed = is_new or _val(old_instance.system_status) != _val(self.system_status)
        if is_new:
            review_status_changed = _val(self.review_status) != _val(self.ReviewStatus.PENDING_TRIAGE)
        else:
            review_status_changed = _val(old_instance.review_status) != _val(self.review_status)

        # Sincronizar reatividade humana (Review afeta System)
        if review_status_changed:
            #Review = DOABLE  && System = UNATTEMPTED => System = PENDING_UPSOLVE
            if self.review_status == self.ReviewStatus.DOABLE and self.system_status == self.SystemStatus.UNATTEMPTED:
                self.system_status = self.SystemStatus.PENDING_UPSOLVE
            #Review = DONE && System = UNATTEMPTED => System = UPSOLVED
            elif self.review_status == self.ReviewStatus.DONE and self.system_status not in [self.SystemStatus.SOLVED_LIVE, self.SystemStatus.PRACTICE_AC, self.SystemStatus.UPSOLVED]:
                self.system_status = self.SystemStatus.UPSOLVED

        # Sincronizar reatividade técnica (System afeta Review)
        if system_status_changed:
            protected_states = [_val(self.ReviewStatus.DONE), _val(self.ReviewStatus.TEAM_DONE), _val(self.ReviewStatus.IGNORED)]
            
            # Definir proteção contra rebaixamento do sucesso (ou lixo) anterior
            is_protected = not is_new and _val(old_instance.review_status) in protected_states
            
            # Ignorar proteção se houver mudança manual simultânea (correção de misclick)
            if review_status_changed:
                is_protected = False
            
            # Promover para sucesso caso o sistema detecte Acerto
            if self.system_status in [self.SystemStatus.SOLVED_LIVE, self.SystemStatus.PRACTICE_AC, self.SystemStatus.UPSOLVED]:
                self.review_status = self.ReviewStatus.DONE
                
            # Aplicar estados inferiores caso não haja proteção ou intervenção manual impedindo
            elif not is_protected:
                if self.system_status in [self.SystemStatus.PENDING_UPSOLVE, self.SystemStatus.PRACTICE_WA]:
                    self.review_status = self.ReviewStatus.DOABLE
                elif self.system_status == self.SystemStatus.UNATTEMPTED:
                    if not review_status_changed:
                        self.review_status = self.ReviewStatus.PENDING_TRIAGE

    def save(self, *args, **kwargs):
        """
        Extrair estado antigo do banco e delegar sincronização de estados da Máquina.
        """
        old_instance = None
        if self.pk is not None:
            try:
                old_instance = UserProblemTracking.objects.get(pk=self.pk)
            except UserProblemTracking.DoesNotExist:
                pass

        self._sync_system_to_review(old_instance)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.problem.platform_id} ({self.system_status})"