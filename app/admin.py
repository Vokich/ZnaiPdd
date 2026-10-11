from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from .models import Profile, TestResult, TeacherLessonReport, Certificate, RoadSign, UserSignProgress


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name = 'Профиль'
    verbose_name_plural = 'Профиль'
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'get_full_name', 'get_role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'profile__role')
    search_fields = ('username', 'email', 'profile__surname1', 'profile__name', 'profile__school')
    ordering = ('-date_joined',)

    def get_full_name(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.full_name
        return '—'
    get_full_name.short_description = 'ФИО'

    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '—'
    get_role.short_description = 'Роль'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'surname1', 'name', 'surname2', 'role', 'school', 'region', 'birth_date')
    list_filter = ('role', 'region', 'school')
    search_fields = ('user__username', 'user__email', 'surname1', 'name', 'surname2', 'school', 'region')
    readonly_fields = ('user',)
    list_per_page = 30

    fieldsets = (
        ('Пользователь', {'fields': ('user', 'role')}),
        ('Личные данные', {'fields': ('surname1', 'name', 'surname2', 'birth_date')}),
        ('Образование', {'fields': ('school', 'region', 'position')}),
    )


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test_type', 'score', 'total_questions', 'passed', 'completed_at')
    list_filter = ('test_type', 'passed', 'completed_at')
    search_fields = ('user__username', 'user__profile__surname1', 'user__profile__name')
    date_hierarchy = 'completed_at'
    readonly_fields = ('completed_at',)
    list_per_page = 30


@admin.register(TeacherLessonReport)
class TeacherLessonReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson_date', 'location', 'children_count', 'photo_link', 'created_at')
    list_filter = ('lesson_date', 'created_at')
    search_fields = ('user__username', 'user__profile__surname1', 'user__profile__name', 'location', 'children_list')
    date_hierarchy = 'lesson_date'
    readonly_fields = ('created_at',)
    list_per_page = 30

    fieldsets = (
        ('Педагог', {'fields': ('user',)}),
        ('Урок', {'fields': ('lesson_date', 'location', 'children_count', 'children_list')}),
        ('Материалы', {'fields': ('photo_link', 'certificate_generated')}),
        ('Служебное', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user', 'test_type', 'document_type', 'download_count', 'generated_at')
    list_filter = ('test_type', 'document_type', 'generated_at')
    search_fields = ('user__username', 'user__profile__surname1', 'user__profile__name')
    date_hierarchy = 'generated_at'
    readonly_fields = ('generated_at', 'download_count')
    list_per_page = 30


admin.site.site_header = 'Админ-панель «Знай ПДД»'
admin.site.site_title = 'Знай ПДД'
admin.site.index_title = 'Управление сайтом'

@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'order', 'image_preview')
    list_filter = ('category',)
    search_fields = ('name',)
    list_editable = ('order',)
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'slug', 'category', 'image', 'order')
        }),
        ('Описание', {
            'fields': ('short_description', 'full_description', 'fun_fact')
        }),
        ('Тест', {
            'fields': ('question', 'answer_options', 'correct_answer'),
            'description': 'Варианты ответов — JSON-массив: ["Вариант 1", "Вариант 2", "Вариант 3"]'
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 60px;" />', obj.image.url)
        return '—'
    image_preview.short_description = 'Превью'


@admin.register(UserSignProgress)
class UserSignProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'sign', 'unlocked', 'test_passed_at')
    list_filter = ('unlocked', 'sign')
    search_fields = ('user__username', 'sign__name')