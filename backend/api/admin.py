from django.contrib import admin
from django.utils.html import format_html
from .models import User, Team, Contest, Problem, ContestParticipation, Submission, UserProblemTracking

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'cf_handle', 'atcoder_handle')
    search_fields = ('username', 'atcoder_handle', 'cf_handle')

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('platform', 'platform_id', 'name')
    list_filter = ('platform',)

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('platform_id', 'get_platform_badge', 'title', 'get_rating', 'get_tags')
    list_filter = ('platform',)
    search_fields = ('platform_id', 'title')

    def get_platform_badge(self, obj):
        color = "#1f77b4" if obj.platform == 'CF' else "#e67e22"
        return format_html('<span style="background: {}; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">{}</span>', 
                           color, obj.get_platform_display())
    get_platform_badge.short_description = 'Plataforma'

    def get_rating(self, obj):
        rating = obj.platform_metadata.get('rating')
        if rating:
            color = "green" if int(rating) < 1200 else ("orange" if int(rating) < 1900 else "red")
            return format_html('<b style="color: {};">{}</b>', color, rating)
        return "-"
    get_rating.short_description = 'Rating'

    def get_tags(self, obj):
        tags = obj.platform_metadata.get('tags', [])
        return ", ".join(tags) if tags else "-"
    get_tags.short_description = 'Tags'

@admin.register(ContestParticipation)
class ContestParticipationAdmin(admin.ModelAdmin):
    list_display = ('contest', 'user', 'team', 'is_virtual')

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('platform_submission_id', 'get_platform', 'problem', 'user', 'participant_type', 'verdict', 'creation_time')
    list_filter = ('problem__platform', 'participant_type', 'verdict')
    search_fields = ('platform_submission_id', 'user__username', 'problem__platform_id')
    
    def get_platform(self, obj):
        return obj.problem.get_platform_display()
    get_platform.short_description = 'Plataforma'

@admin.register(UserProblemTracking)
class UserProblemTrackingAdmin(admin.ModelAdmin):
    list_display = ('user','problem', 'get_system_status_badge', 'get_review_status_badge')
    list_filter = ('problem__platform', 'system_status', 'review_status')
    search_fields = ('user__username', 'problem__platform_id')
    raw_id_fields = ('problem', 'user')

    def get_system_status_badge(self, obj):
        colors = {
            'SOLVED_LIVE': '#2ecc71', # Green
            'UPSOLVED': '#27ae60',   # Darker Green
            'PRACTICE_AC': '#2ecc71',# Green
            'PENDING_UPSOLVE': '#e74c3c', # Red
            'PRACTICE_WA': '#e67e22', # Orange
            'UNATTEMPTED': '#95a5a6', # Gray
        }
        color = colors.get(obj.system_status, "#000")
        return format_html('<span style="color: {}; font-weight: bold;">● {}</span>', 
                           color, obj.get_system_status_display())
    get_system_status_badge.short_description = 'Status Técnico'

    def get_review_status_badge(self, obj):
        colors = {
            'DONE': '#1abc9c',
            'TEAM_DONE': '#3498db',
            'DOABLE': '#f1c40f',
            'IGNORED': '#34495e',
            'PENDING_TRIAGE': '#9b59b6',
        }
        color = colors.get(obj.review_status, "#000")
        return format_html('<span style="background: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">{}</span>', 
                           color, obj.get_review_status_display())
    get_review_status_badge.short_description = 'Sua Revisão'
