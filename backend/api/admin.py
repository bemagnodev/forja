from django.contrib import admin
from django.utils.html import format_html
from .models import Contest, Problem, Submission

@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('external_id', 'name', 'contest_type', 'platform', 'is_team', 'has_full_problem_set')
    list_display_links = ('external_id', 'name')
    search_fields = ('name', 'external_id')
    list_filter = ('contest_type', 'platform', 'is_team', 'has_full_problem_set')
    ordering = ('-external_id',)

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('index', 'name', 'colored_status', 'live_performance', 'rating', 'contest__name', )
    list_display_links = ('index', 'name')
    search_fields = ('name', 'contest__name') # __name busca no nome do contest relacionado
    list_filter = ('resolution_status', 'live_performance', 'contest__contest_type', 'contest__platform', 'rating')
    ordering = ('contest__external_id', 'index')
    # Função auxiliar para mostrar a coluna "Platform" na tabela de Problemas
    @admin.display(description='Platform', ordering='contest__platform')
    def get_platform(self, obj):
        return obj.contest.platform
    
    # Lógica de cores paraSTATUS
    @admin.display(description='Status Atual', ordering='resolution_status')
    def colored_status(self, obj):
        if obj.resolution_status in ['SOLVED_LIVE', 'UPSOLVED', 'SOLVED_PRACTICE']:
            color = '#28a745' 
            weight = 'bold'
        elif obj.resolution_status == 'PENDING':
            color = '#dc3545' 
            weight = 'bold'
        else:
            color = '#6c757d' 
            weight = 'normal'

        return format_html(
            '<span style="color: {}; font-weight: {};">{}</span>',
            color,
            weight,
            obj.get_resolution_status_display()
        )

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('submission_id', 'problem', 'colored_verdict', 'is_after_contest', 'creation_time', 'get_platform')
    list_display_links = ('submission_id', 'problem')
    search_fields = ('submission_id','problem__name', 'problem__contest__name')
    list_filter = ('problem__contest__platform', 'verdict', 'creation_time')

    @admin.display(description='Platform', ordering='problem__contest__platform')
    def get_platform(self, obj):
        return obj.problem.contest.platform
    
    # Lógica de cores
    @admin.display(description='Verdict', ordering='verdict')
    def colored_verdict(self, obj):
        if obj.verdict == 'OK':
            color = '#28a745' # Verde Sucesso
            icon = '✔'
        elif obj.verdict == 'TESTING':
            color = '#ffc107' # Amarelo
            icon = '⏳'
        else:
            color = '#dc3545' # Vermelho Erro
            icon = '✖'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.verdict
        )