from uuid import uuid4

from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.html import format_html, format_html_join

from app.models import PlatformAttempt, RouteResult, RouteSceneContent
from app.routes.engine import STARTER_SCENES
from app.routes.levels import LEVELS, published_levels, with_route_title


@admin.register(RouteSceneContent)
class RouteSceneAdmin(admin.ModelAdmin):
    list_display = ('title', 'rule')
    search_fields = ('title', 'prompt')

    def has_delete_permission(self, request, obj=None):
        return bool(obj and obj.key not in STARTER_SCENES and super().has_delete_permission(request, obj))

    def get_form(self, request, obj=None, **kwargs):
        choices = obj.choices if obj else [dict(id=f'option-{n}', label='', feedback='', safe=n == 1) for n in range(1, 4)]
        fields = {'title': forms.CharField(label='Название', max_length=150),
                  'prompt': forms.CharField(label='Описание', widget=forms.Textarea)}
        if not obj or obj.key not in STARTER_SCENES:
            fields['pool'] = forms.ChoiceField(label='Добавлять в маршруты', choices=[('walk', 'Пешком'), ('bike', 'На велосипеде')])
        if not obj or obj.rule:
            fields['rule'] = forms.CharField(label='Пункт правил', max_length=120)
            fields['url'] = forms.URLField(label='Ссылка на правило', max_length=500)
        for index, choice in enumerate(choices, 1):
            fields[f'label_{index}'] = forms.CharField(label=f'Действие {index}', max_length=300, initial=choice['label'])
            if not obj or choice['feedback']:
                fields[f'feedback_{index}'] = forms.CharField(label=f'Объяснение {index}', max_length=900,
                                                            initial=choice['feedback'], widget=forms.Textarea)
            if not obj or obj.key not in ('works', 'park', 'walkway', 'home'):
                fields[f'safe_{index}'] = forms.BooleanField(label='Безопасное действие', required=False, initial=choice['safe'])

        class SceneForm(forms.ModelForm):
            def clean(self):
                values = super().clean()
                rows = [dict(row) for row in choices]
                for index, row in enumerate(rows, 1):
                    for field in ('label', 'feedback', 'safe'):
                        if f'{field}_{index}' in values:
                            row[field] = values[f'{field}_{index}']
                if rows and not any(row['safe'] for row in rows):
                    raise forms.ValidationError('Выберите хотя бы одно безопасное действие.')
                if self.instance._state.adding:
                    self.instance.key = 'scene-' + uuid4().hex
                self.instance.choices = rows
                return values

        form = type('SceneEditor', (SceneForm,), fields.copy())
        return forms.modelform_factory(RouteSceneContent, form=form, fields=tuple(fields))


class RouteLevelFilter(admin.SimpleListFilter):
    title = 'Уровень'
    parameter_name = 'level'

    def lookups(self, request, model_admin):
        return [(key, level['title']) for key, level in published_levels().items()]

    def queryset(self, request, queryset):
        if self.value() in LEVELS:
            return queryset.filter(**{self.parameter_name: self.value()})
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
    fields = ('attempt', 'user', 'level', 'total', 'score', 'mistakes', 'completed_at', 'rule_reviews', 'opened_rules')
    readonly_fields = ('completed_at', 'opened_rules')

    def get_queryset(self, request):
        return with_route_title(super().get_queryset(request), 'level')

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        PlatformAttempt.objects.filter(source='route:' + obj.pk).update(score=obj.score, total=obj.total)

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
        return result.route_title

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
