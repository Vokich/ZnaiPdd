from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .media import prepare_image
from .models import NewsImage, PracticeImage


class MultiImageInput(forms.FileInput):
    allow_multiple_selected = True


class GalleryUploads(forms.ImageField):
    def __init__(self):
        super().__init__(
            label='Добавить изображения', required=False, widget=MultiImageInput(attrs={'accept': 'image/*'}),
            help_text='Можно выбрать несколько файлов. Подписи и порядок редактируются после сохранения.',
        )

    def clean(self, data, initial=None):
        clean_one = super().clean
        return [prepare_image(clean_one(upload), keep_transparency=True) for upload in (data or [])]


class GalleryImageForm(forms.ModelForm):
    def clean_image(self):
        return prepare_image(self.cleaned_data['image'], keep_transparency=True)


def image_preview(image):
    if not image:
        return '—'
    return format_html(
        '<a href="{}" target="_blank" rel="noopener noreferrer"><img src="{}" alt="Предпросмотр" '
        'style="max-width:120px; max-height:85px; object-fit:contain;"></a>',
        image.url, image.url,
    )


class GalleryInline(admin.TabularInline):
    form = GalleryImageForm
    fields = ('preview', 'image', 'caption', 'alt', 'order')
    readonly_fields = ('preview',)
    extra = 0

    @admin.display(description='Предпросмотр')
    def preview(self, item):
        return image_preview(item.image)


class NewsImageInline(GalleryInline):
    model = NewsImage


class PracticeImageInline(GalleryInline):
    model = PracticeImage

    def has_change_permission(self, request, obj=None):
        return (obj is None or obj.published_at is None) and super().has_change_permission(request, obj)

    def has_add_permission(self, request, obj=None):
        return (obj is None or obj.published_at is None) and super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return (obj is None or obj.published_at is None) and super().has_delete_permission(request, obj)
