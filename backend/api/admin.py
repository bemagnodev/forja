from django.contrib import admin
from django.utils.html import format_html
from .models import Contest, Problem, Submission

@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ( 'external_id', 'name', 'start_time','platform','is_team')
    list_display_links = ('external_id', 'name')
    search_fields = ('name', 'external_id')
    list_filter = ('platform', 'is_team', 'start_time')
    
    # Ordenação padrão (mais recentes primeiro)
    ordering = ('-start_time',)

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('index', 'name', 'contest',  'rating', 'is_solved', 'get_platform')
    list_display_links = ('index', 'name')
    search_fields = ('name', 'contest__name') # __name busca no nome do contest relacionado
    list_filter = ('contest__platform', 'is_solved', 'rating')
    
    # Função auxiliar para mostrar a coluna "Platform" na tabela de Problemas
    @admin.display(description='Platform', ordering='contest__platform')
    def get_platform(self, obj):
        return obj.contest.platform

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('submission_id', 'problem', 'colored_verdict', 'creation_time', 'get_platform')
    list_display_links = ('submission_id', 'problem')
    search_fields = ('submission_id', 'problem__name')
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