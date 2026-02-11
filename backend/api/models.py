from django.db import models

class Contest(models.Model):
    external_id = models.IntegerField(unique=True, help_text="ID original do Codeforces")
    name = models.CharField(max_length=255)
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
    
    class Meta:
        #impede dois problemas com mesmo index em um unico contest (Ex: dois A)
        unique_together = ('contest', 'index')
        
    def __str__(self):
        return f"{self.index} - {self.name}"
    
class Submission(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')  
    
    verdict = models.CharField(max_length=50) #OK, TLE, MLE, WA
    submission_id = models.IntegerField(unique=True)
    creation_time = models.DateTimeField()
    is_upsolved = models.BooleanField(default=False)  


    def __str__(self):
        return f"{self.submission_id} - {self.verdict}"