from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import path, reverse
from django.utils.html import format_html

from app.documents.certificates import award_download
from app.models import AgeTestQuestion, PlatformAttempt, TestResult


class AnswerLinesField(forms.CharField):
    def prepare_value(self, value):
        return '\n'.join(value) if isinstance(value, list) else value

    def to_python(self, value):
        return [line.strip() for line in super().to_python(value).splitlines()]


class AgeTestQuestionForm(forms.ModelForm):
    options = AnswerLinesField(
        label='Варианты ответа', help_text='Введите каждый вариант с новой строки. Нумерация начинается с 1.',
        widget=forms.Textarea(attrs={'rows': 5, 'cols': 80}),
    )

    class Meta:
        model = AgeTestQuestion
        fields = '__all__'


@admin.register(AgeTestQuestion)
class AgeTestQuestionAdmin(admin.ModelAdmin):
    form = AgeTestQuestionForm
    list_display = ('test_type', 'number', 'text', 'reference')
    list_filter = ('test_type',)
    search_fields = ('text', 'reference')


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        source = f'age:{obj.pk}'
        defaults = dict(kind='age', user=obj.user, task=obj.test_type, title=obj.get_test_type_display(),
                        score=obj.score, total=obj.total_questions, completed_at=obj.completed_at)
        PlatformAttempt.objects.update_or_create(source=source, defaults=defaults)

    @admin.display(description='Документ')
    def award(self, obj):
        if obj.passed and obj.score >= obj.passing_score:
            return format_html('<a href="{}">Сформировать PDF</a>', reverse('admin:platform_award', args=[obj.pk]))
        return '—'

    def get_urls(self):
        return [path('<int:pk>/award/', self.admin_site.admin_view(self.download), name='platform_award')] + super().get_urls()

    def download(self, request, pk):
        if not request.user.is_superuser:
            raise PermissionDenied
        obj = self.get_object(request, str(pk))
        if not obj or not obj.passed or obj.score < obj.passing_score:
            raise Http404
        return award_download(obj)

    list_display = ('user', 'test_type', 'score', 'total_questions', 'passed', 'completed_at', 'award')
    list_filter = ('test_type', 'passed', 'completed_at')
    search_fields = ('user__username', 'user__profile__surname1', 'user__profile__name')
    date_hierarchy = 'completed_at'
    readonly_fields = ('completed_at',)
    list_per_page = 30
