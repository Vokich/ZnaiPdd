from django.contrib import admin

from app.classroom.forms import TeacherLessonReportForm
from app.models import TeacherLessonReport
from app.routes.admin import RouteLevelFilter
from app.routes.levels import with_route_title


class ReportRouteFilter(RouteLevelFilter):
    parameter_name = 'route_level'

    def lookups(self, request, model_admin):
        return [*super().lookups(request, model_admin), ('none', 'Без маршрута')]

    def queryset(self, request, queryset):
        if self.value() == 'none':
            return queryset.filter(route_level='')
        return super().queryset(request, queryset)



@admin.register(TeacherLessonReport)
class TeacherLessonReportAdmin(admin.ModelAdmin):
    form = TeacherLessonReportForm
    list_display = ('user', 'lesson_date', 'organization', 'location', 'participants_count', 'route_name', 'practice', 'completed_count', 'created_at')
    list_select_related = ('user', 'organization__municipality', 'practice')
    list_filter = ('lesson_date', ReportRouteFilter, 'created_at')
    search_fields = ('user__username', 'organization__name', 'location')
    date_hierarchy = 'lesson_date'
    readonly_fields = ('created_at', 'certificate_generated', 'classroom_info')
    autocomplete_fields = ('user', 'organization')
    list_per_page = 30

    def get_queryset(self, request):
        return with_route_title(super().get_queryset(request), 'route_level')

    @admin.display(description='Уровень безопасного маршрута')
    def route_name(self, report):
        return report.route_title or '—'

    def get_readonly_fields(self, request, obj=None):
        return (*self.readonly_fields, 'user') if obj else self.readonly_fields

    fieldsets = (
        ('Педагог', {'fields': ('user',)}),
        ('Урок', {'fields': ('lesson_date', 'organization', 'location', 'participants_count')}),
        ('Учебное задание', {'fields': ('classroom_info', 'route_level', 'practice', 'completed_count')}),
        ('Служебное', {'fields': ('created_at', 'certificate_generated'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Занятие')
    def classroom_info(self, obj):
        if not obj or not obj.classroom_id:
            return 'Ручной отчёт'
        from app.classroom.lessons import run_title
        run = obj.classroom
        mode = 'Разобрали вместе' if run.lesson else f'Тест по QR · отправлено {run.summary["submitted"]}'
        return f'{run_title(run)} · {mode}'
