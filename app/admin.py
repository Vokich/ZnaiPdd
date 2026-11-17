from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.html import format_html, format_html_join
from .access import ADMIN, account_role
from .forms import TeacherLessonReportForm
from .models import Certificate, Municipality, Organization, Profile, RoadSign, RouteResult, TeacherLessonReport, TestResult, UserSignProgress
from .route_levels import LEVELS
from . import editorial_admin


ACCOUNT_ROLES = {**dict(Profile.Role.choices), ADMIN: 'Администратор'}


class AccountFields(forms.ModelForm):
    account_role = forms.ChoiceField(label='Профиль доступа', choices=ACCOUNT_ROLES.items())
    surname1 = forms.CharField(label='Фамилия', max_length=50, required=False)
    name = forms.CharField(label='Имя', max_length=50, required=False)
    surname2 = forms.CharField(label='Отчество', max_length=50, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'profile', None)
        self.initial['account_role'] = account_role(self.instance) or Profile.Role.CHILD
        if profile:
            for field in ('surname1', 'name', 'surname2'):
                self.initial[field] = getattr(profile, field)


class AccountChangeForm(AccountFields, UserChangeForm):
    pass


class AccountCreationForm(AccountFields, AdminUserCreationForm):
    pass


class UserAdmin(BaseUserAdmin):
    form = AccountChangeForm
    add_form = AccountCreationForm
    list_display = ('username', 'email', 'get_full_name', 'account_role', 'is_active')
    list_filter = ('is_active',)
    list_select_related = ('profile',)
    search_fields = ('username', 'email', 'profile__surname1', 'profile__name', 'profile__school')
    ordering = ('-date_joined',)
    personal_fields = ('surname1', 'name', 'surname2', 'email')
    fieldsets = (
        (None, {'fields': ('username', 'password', 'account_role', 'is_active')}),
        ('Личные данные', {'fields': personal_fields}),
    )
    add_fieldsets = (
        (None, {'fields': ('username', 'usable_password', 'password1', 'password2', 'account_role')}),
        ('Личные данные', {'fields': personal_fields}),
    )

    @admin.display(description='ФИО')
    def get_full_name(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.full_name if profile else '—'

    @admin.display(description='Профиль доступа')
    def account_role(self, obj):
        return ACCOUNT_ROLES.get(account_role(obj), 'Нужно завершить настройку')

    def get_readonly_fields(self, request, obj=None):
        return ('account_role', 'is_active') if obj and request.user.pk == obj.pk else ()

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and (obj is None or request.user.pk != obj.pk)

    def save_model(self, request, obj, form, change):
        role = form.cleaned_data.get('account_role', account_role(obj))
        obj.is_staff = obj.is_superuser = role == ADMIN
        super().save_model(request, obj, form, change)
        fields = {field: form.cleaned_data[field] for field in ('surname1', 'name', 'surname2')}
        fields['role'] = Profile.Role.CHILD if role == ADMIN else role
        Profile.objects.update_or_create(user=obj, defaults=fields)


admin.site.unregister(Group)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('name', 'code')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality')
    list_select_related = ('municipality',)
    search_fields = ('name', 'municipality__name')
    autocomplete_fields = ('municipality',)


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test_type', 'score', 'total_questions', 'passed', 'completed_at')
    list_filter = ('test_type', 'passed', 'completed_at')
    search_fields = ('user__username', 'user__profile__surname1', 'user__profile__name')
    date_hierarchy = 'completed_at'
    readonly_fields = ('completed_at',)
    list_per_page = 30


class RouteLevelFilter(admin.SimpleListFilter):
    title = 'Уровень'
    parameter_name = 'level'

    def lookups(self, request, model_admin):
        return [(key, level['title']) for key, level in LEVELS.items()]

    def queryset(self, request, queryset):
        if self.value() in LEVELS:
            return queryset.filter(level=self.value())
        return queryset


@admin.register(RouteResult)
class RouteResultAdmin(admin.ModelAdmin):
    list_display = ('participant', 'route_level', 'points', 'mistakes', 'completed_at')
    list_select_related = ('user__profile',)
    list_filter = (RouteLevelFilter, 'completed_at')
    search_fields = ('user__username', 'user__profile__surname1', 'user__profile__name', 'user__profile__surname2')
    ordering = ('-completed_at', '-pk')
    date_hierarchy = 'completed_at'
    list_per_page = 30
    fields = ('participant', 'route_level', 'total_points', 'score', 'mistakes', 'completed_at', 'opened_rules')
    readonly_fields = ('participant', 'route_level', 'total_points', 'completed_at', 'opened_rules')

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Участник', ordering='user__username')
    def participant(self, result):
        profile = getattr(result.user, 'profile', None)
        if profile:
            name = ' '.join(filter(None, (profile.surname1, profile.name, profile.surname2)))
            if name:
                return f'{name} ({result.user.get_username()})'
        return result.user.get_username()

    @admin.display(description='Уровень')
    def route_level(self, result):
        return LEVELS.get(result.level, {}).get('title', result.level)

    @admin.display(description='Баллы', ordering='score')
    def points(self, result):
        return f'{result.score} из {result.total}'

    @admin.display(description='Максимум баллов')
    def total_points(self, result):
        return result.total

    @admin.display(description='Переходы к пунктам ПДД')
    def opened_rules(self, result):
        links = []
        for review in result.rule_reviews:
            timestamp = review.get('opened_at')
            if timestamp:
                opened = timezone.localtime(parse_datetime(timestamp))
                links.append((review['rule'], opened.strftime('%d.%m.%Y %H:%M:%S')))
        if not links:
            return '—'
        items = format_html_join('', '<li>{} · {}</li>', links)
        return format_html('<ul>{}</ul>', items)


@admin.register(TeacherLessonReport)
class TeacherLessonReportAdmin(admin.ModelAdmin):
    form = TeacherLessonReportForm
    list_display = ('user', 'lesson_date', 'organization', 'location', 'participants_count', 'route_level', 'practice', 'completed_count', 'created_at')
    list_select_related = ('user', 'organization__municipality', 'practice')
    list_filter = ('lesson_date', 'route_level', 'created_at')
    search_fields = ('user__username', 'organization__name', 'location')
    date_hierarchy = 'lesson_date'
    readonly_fields = ('created_at', 'certificate_generated')
    autocomplete_fields = ('user', 'organization')
    list_per_page = 30

    def get_readonly_fields(self, request, obj=None):
        return (*self.readonly_fields, 'user') if obj else self.readonly_fields

    fieldsets = (
        ('Педагог', {'fields': ('user',)}),
        ('Урок', {'fields': ('lesson_date', 'organization', 'location', 'participants_count')}),
        ('Учебное задание', {'fields': ('route_level', 'practice', 'completed_count')}),
        ('Служебное', {'fields': ('created_at', 'certificate_generated'), 'classes': ('collapse',)}),
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


class RoadSignAdminForm(forms.ModelForm):
    class Meta:
        model = RoadSign
        fields = '__all__'
        labels = {'slug': 'Адрес знака', 'category': 'Категория'}


@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    form = RoadSignAdminForm
    list_display = ('name', 'number', 'category_label', 'is_published', 'order', 'image_preview')
    list_filter = ('is_published', 'category')
    search_fields = ('number', 'name')
    list_editable = ('order',)
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'number', 'slug', 'category', 'order', 'is_published')
        }),
        ('Описание', {
            'fields': ('short_description', 'full_description', 'fun_fact')
        }),
        ('Источники', {
            'fields': ('image', 'image_credit', 'source_url', 'reviewed_on')
        }),
        ('Тест', {
            'fields': ('question', 'answer_options', 'correct_answer'),
            'description': 'Варианты ответов — JSON-массив: ["Вариант 1", "Вариант 2", "Вариант 3"]'
        }),
    )

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" alt="" style="max-height: 60px;" />', obj.image_url)
        return '—'
    image_preview.short_description = 'Превью'

    @admin.display(description='Категория', ordering='category')
    def category_label(self, obj):
        return obj.get_category_display()


@admin.register(UserSignProgress)
class UserSignProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'sign', 'unlocked', 'test_passed_at')
    list_filter = ('unlocked', 'sign')
    search_fields = ('user__username', 'sign__name')
