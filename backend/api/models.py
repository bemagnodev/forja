from django.db import models

class Contest(models.Model):

    class Platform(models.TextChoices):
        CODEFORCES = 'CF', 'Codeforces'
        CSES = 'CSES', 'CSES'
        # Futuro: ATCODER = 'AC', 'AtCoder'

    class ContestType(models.TextChoices):
        OFFICIAL = 'LIVE', 'Oficial'
        VIRTUAL = 'VIRTUAL', 'Virtual'
        PRACTICE = 'PRACTICE', 'Prática'

    external_id = models.IntegerField(unique=True, help_text="ID original do Codeforces")
    name = models.CharField(max_length=255)

    platform = models.CharField(
        max_length=10,
        choices=Platform.choices,
        default=Platform.CODEFORCES  
    )

    contest_type = models.CharField(max_length=10, choices=ContestType.choices, default=ContestType.PRACTICE)
    
    is_team = models.BooleanField(
        default=False, 
        help_text="True se feito em equipe. Habilita a verificação de 'Resolvido pelo Time' nas questões."
    )

    # Campos exclusivos para LIVE e VIRTUAL
    start_time = models.DateTimeField(
        null=True, blank=True, 
        help_text="Obrigatório para LIVE/VIRTUAL. Define o Marco Zero para saber se a submissão foi dentro do tempo."
    )
    
    duration_minutes = models.IntegerField(
        null=True, blank=True, 
        help_text="Obrigatório para LIVE/VIRTUAL. Ex: 120. Somado ao start_time, define a 'Janela da Prova'."
    )
    
    rank_achieved = models.IntegerField(
        null=True, blank=True, 
        help_text="Opcional. Posição final apenas para provas oficiais/virtuais."
    )
    has_full_problem_set = models.BooleanField(
        default=False, 
        help_text="Indica se todos os problemas deste contest já foram baixados via API de Standings."
    )

    def __str__(self):
        return f"{self.name} ({self.external_id})"
    
class Problem(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='problems')
    index = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    rating = models.IntegerField(null=True, blank=True)
    tags = models.JSONField(default=list)  
    is_favorite = models.BooleanField(default=False)
    xp_value = models.IntegerField(default=0, help_text="XP calculado via IA/Fórmula")

    solved_by_me_in_team = models.BooleanField(
        default=False, 
        help_text="Marque se VOCÊ codou essa questão no contest em time."
    )

    class LivePerformance(models.TextChoices):
        NOT_PARTICIPATED = 'NOT_PARTICIPATED', 'Fora de Contest' # Para questões soltas/Practice
        UNATTEMPTED = 'UNATTEMPTED', 'Não tentada' # Estava no contest, mas você não submeteu nada
        FAILED = 'FAILED', 'Erro (WA/TLE)'
        AC_SOLO = 'AC_SOLO', 'Eu resolvi (AC)'
        AC_TEAM = 'AC_TEAM', 'Time resolveu' # Só faz sentido se contest.is_team == True

    live_performance = models.CharField(
        max_length=25, 
        choices=LivePerformance.choices, 
        default=LivePerformance.NOT_PARTICIPATED,
        help_text="O que aconteceu DURANTE a janela de tempo do contest."
    )

    class ResolutionStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendente'
        UPSOLVED = 'UPSOLVED', 'Upsolvado'
        SOLVED_LIVE = 'SOLVED_LIVE', 'AC Contest'
        SOLVED_PRACTICE = 'SOLVED_PRACTICE', 'AC Prática' 
        NOT_REQUIRED = 'NOT_REQUIRED', 'Futuro'

    resolution_status = models.CharField(
        max_length=20, 
        choices=ResolutionStatus.choices, 
        default=ResolutionStatus.PENDING
    )

    def update_state_from_submission(self, is_after, is_team_submission, verdict):
        """
        Máquina de Estados Isolada:
        Recebe os dados de uma submissão e calcula o novo status do problema.
        """
        # Se questão ja foi resolvida alguma vez, status não muda
        already_solved = self.resolution_status in [
            self.ResolutionStatus.SOLVED_LIVE, 
            self.ResolutionStatus.UPSOLVED, 
            self.ResolutionStatus.SOLVED_PRACTICE
        ]

        if verdict == 'OK':
            if not is_after:
                # CASO 1: Sucesso durante o contest (Live/Virtual)
                if is_team_submission and self.solved_by_me_in_team:
                    self.live_performance = self.LivePerformance.AC_SOLO
                    self.resolution_status = self.ResolutionStatus.SOLVED_LIVE
                elif is_team_submission:
                    self.live_performance = self.LivePerformance.AC_TEAM
                    self.resolution_status = self.ResolutionStatus.PENDING
                else:
                    self.live_performance = self.LivePerformance.AC_SOLO
                    self.resolution_status = self.ResolutionStatus.SOLVED_LIVE
            else:
                # CASO 2: Sucesso fora do tempo oficial
                if self.resolution_status != self.ResolutionStatus.SOLVED_LIVE:
                    
                    debitos_anteriores = [
                        self.LivePerformance.FAILED, 
                        self.LivePerformance.AC_TEAM, 
                        self.LivePerformance.UNATTEMPTED
                    ]
                    if self.live_performance in debitos_anteriores:
                        self.resolution_status = self.ResolutionStatus.UPSOLVED
                    else:
                        if self.resolution_status != self.ResolutionStatus.UPSOLVED:
                            self.resolution_status = self.ResolutionStatus.SOLVED_PRACTICE
        else:
            # CASO 3: Erro durante a prova gera dívida imediata (PENDING)
            if not is_after:
                if self.live_performance not in [self.LivePerformance.AC_SOLO, self.LivePerformance.AC_TEAM]:
                    self.live_performance = self.LivePerformance.FAILED
            
            if not already_solved:
                self.resolution_status = self.ResolutionStatus.PENDING

        self.save()

    def save(self, *args, **kwargs):
        """
        Intercepta o salvamento do banco para garantir que mudanças manuais 
        no Admin (como a flag do time) atualizem a Máquina de Estados.
        """
        # seo contest foi em time
        if self.contest and self.contest.is_team:
            # Se resolvida por mim e o status estava como Time -> soved_by_me
            if self.solved_by_me_in_team and self.live_performance == self.LivePerformance.AC_TEAM:
                self.live_performance = self.LivePerformance.AC_SOLO
                self.resolution_status = self.ResolutionStatus.SOLVED_LIVE
                
            # Se estava como feita por mim e mudou -> Devolve pro Time
            elif not self.solved_by_me_in_team and self.live_performance == self.LivePerformance.AC_SOLO:
                self.live_performance = self.LivePerformance.AC_TEAM
                if self.resolution_status == self.ResolutionStatus.SOLVED_LIVE:
                    self.resolution_status = self.ResolutionStatus.PENDING

        super().save(*args, **kwargs)

    class Meta:
        #impede dois problemas com mesmo index em um unico contest (Ex: dois A)
        unique_together = ('contest', 'index')
        
    def __str__(self):
        return f"{self.index} - {self.name}"
    
class Submission(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')  
    
    submission_id = models.IntegerField(unique=True)
    verdict = models.CharField(max_length=50) #OK, TLE, MLE, WA
    creation_time = models.DateTimeField()
    is_after_contest = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.submission_id} - {self.verdict}"