from django.contrib import admin
from .models import Contest, Problem, Submission

@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('external_id', 'name', 'start_time', 'is_team')
    search_fields = ('name', 'external_id')
    list_filter = ('is_team', 'start_time')
    
    # Ordenação padrão (mais recentes primeiro)
    ordering = ('-start_time',)

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('name', 'contest', 'index', 'rating')
    search_fields = ('name', 'contest__name') # __name busca no nome do contest relacionado
    list_filter = ('rating', 'index')

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('submission_id', 'problem', 'verdict', 'creation_time', 'is_upsolved')
    search_fields = ('submission_id', 'problem__name')
    list_filter = ('verdict', 'is_upsolved', 'creation_time')