from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.urls import path
from django.utils.html import format_html_join

from app.models import PlatformAttempt
from app.reporting.excel import export_attempts


@admin.register(PlatformAttempt)
class PlatformAttemptAdmin(admin.ModelAdmin):
    change_list_template = 'admin/app/platformattempt/change_list.html'
    list_display = ('completed_at', 'title', 'user', 'organization', 'score', 'total')
    list_filter = ('kind', 'completed_at', 'organization')
    search_fields = ('title', 'task', 'user__username', 'user__profile__surname1', 'user__profile__name', 'organization')
    date_hierarchy = 'completed_at'
    fields = ('completed_at', 'kind', 'title', 'version', 'user', 'organization', 'score', 'total', 'details')
    readonly_fields = fields
    list_per_page = 40

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    has_delete_permission = has_change_permission

    @admin.display(description='Ответы по вопросам')
    def details(self, obj):
        return format_html_join('', '<p><b>{}</b><br>Ответ: {}<br>Верный вариант: {} · {}</p>',
            ((r['question'], r['selected'], r['expected'], 'Верно' if r['correct'] else 'Ошибка') for r in obj.answers)
        ) or 'Нет детализации'

    def get_urls(self):
        return [path('excel/', self.admin_site.admin_view(self.excel), name='platform_excel')] + super().get_urls()

    def excel(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        return export_attempts(self.get_changelist_instance(request).queryset)
