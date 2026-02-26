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