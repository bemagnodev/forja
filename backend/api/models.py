from django.db import models

class Contest(models.Model):

    class Platform(models.TextChoices):
        CODEFORCES = 'CF', 'Codeforces'
        CSES = 'CSES', 'CSES'
        # Futuro: ATCODER = 'AC', 'AtCoder'

    external_id = models.IntegerField(unique=True, help_text="ID original do Codeforces")
    name = models.CharField(max_length=255)

    platform = models.CharField(
        max_length=10,
        choices=Platform.choices,
        default=Platform.CODEFORCES  
    )

    start_time = models.DateTimeField(null=True, blank=True)
    is_team = models.BooleanField()
    
    problems_solved_count = models.IntegerField(null=True, blank=True, help_text="Quantos problemas resolvidos durante a prova")
    rank_achieved = models.IntegerField(null=True, blank=True, help_text="Posição final")


    def __str__(self):
        return f"{self.name} ({self.external_id})"
    
class Problem(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='problems')
    
    index = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    rating = models.IntegerField(null=True, blank=True)
    tags = models.JSONField(default=list)  

    is_upsolved = models.BooleanField(default=False)
    # Define se o problema foi resolvido durante o contest pelo time    
    solved_by_team = models.BooleanField(default=False)

    is_solved = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    
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


    def __str__(self):
        return f"{self.submission_id} - {self.verdict}"