from django import forms
from django.contrib import admin
from django.utils.html import format_html

from app.models import RoadSign, UserSignProgress


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
