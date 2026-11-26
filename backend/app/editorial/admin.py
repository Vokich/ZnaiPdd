from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from app.editorial.images import GalleryUploads, NewsImageInline, PracticeImageInline, image_preview
from app.editorial.media import prepare_image
from app.models import NewsPost, PracticeExercise, PracticeVersion
from app.practice.service import copy_practice_version, publish_practice, withdraw_practice


class EditorialAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission

    def has_delete_permission(self, request, obj=None):
        return False

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST' and object_id and object_id.isascii() and object_id.isdecimal() and len(object_id) <= 18:
            with transaction.atomic():
                self.model.objects.select_for_update().filter(pk=object_id).first()
                return super().changeform_view(request, object_id, form_url, extra_context)
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        uploads = form.cleaned_data.get('new_images', [])
        if uploads:
            gallery = form.instance.images
            last = gallery.aggregate(maximum=Max('order'))['maximum'] or 0
            for number, image in enumerate(uploads, start=last + 1):
                gallery.create(image=image, order=number)


class SlugEditorialAdmin(EditorialAdmin):
    prepopulated_fields = {'slug': ('title',)}

    def get_readonly_fields(self, request, obj=None):
        return (*self.readonly_fields, 'slug') if obj else self.readonly_fields

    def get_prepopulated_fields(self, request, obj=None):
        return {} if obj else self.prepopulated_fields


def lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def numbers(text):
    return [int(number) for number in text.split(',')] if text.strip() else []


class PracticeVersionForm(forms.ModelForm):
    new_images = GalleryUploads()
    cards = forms.CharField(label='Карточки действий', widget=forms.Textarea(attrs={'rows': 4}), required=False,
                            help_text='Одна карточка на строку. Номера идут сверху вниз.')
    orders = forms.CharField(label='Допустимые порядки', widget=forms.Textarea(attrs={'rows': 2}), required=False,
                             help_text='Например, 1,2,3. Если порядков несколько, укажите каждый на новой строке.')
    meanings = forms.CharField(label='Варианты смысла основного знака', widget=forms.Textarea(attrs={'rows': 3}), required=False)
    conditions = forms.CharField(label='Варианты условий для обеих табличек', widget=forms.Textarea(attrs={'rows': 4}), required=False)
    right_meanings = forms.CharField(label='Верные номера смысла знака', required=False)
    right_a = forms.CharField(label='Верные номера условия для первой таблички', required=False)
    right_b = forms.CharField(label='Верные номера условия для второй таблички', required=False)

    class Meta:
        model = PracticeVersion
        fields = ('exercise', 'kind', 'prompt', 'explanation', 'source_url', 'sign', 'plate_a', 'plate_b')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        content = self.instance.content
        for key in ('cards', 'meanings', 'conditions'):
            self.initial[key] = '\n'.join(content.get(key, []))
        self.initial['orders'] = '\n'.join(','.join(map(str, order)) for order in content.get('orders', []))
        for key in ('right_meanings', 'right_a', 'right_b'):
            self.initial[key] = ','.join(map(str, content.get(key, [])))

    def clean(self):
        data = super().clean()
        try:
            if data.get('kind') == PracticeVersion.Kind.ORDER:
                self.instance.content = {
                    'cards': lines(data.get('cards', '')),
                    'orders': [numbers(order) for order in lines(data.get('orders', ''))],
                }
            else:
                self.instance.content = {
                    'meanings': lines(data.get('meanings', '')),
                    'conditions': lines(data.get('conditions', '')),
                    **{key: numbers(data.get(key, '')) for key in ('right_meanings', 'right_a', 'right_b')},
                }
        except ValueError as error:
            raise ValidationError('Номера ответов указываются целыми числами через запятую.') from error
        return data


@admin.register(PracticeExercise)
class PracticeExerciseAdmin(SlugEditorialAdmin):
    list_display = ('title', 'topic', 'difficulty', 'published_version')
    list_filter = ('topic', 'difficulty')
    list_select_related = ('published_version',)
    search_fields = ('title', 'slug')
    readonly_fields = ('published_version',)


@admin.register(PracticeVersion)
class PracticeVersionAdmin(EditorialAdmin):
    change_form_template = 'admin/app/practiceversion/change_form.html'
    form = PracticeVersionForm
    inlines = (PracticeImageInline,)
    list_display = ('exercise', 'kind', 'version_status', 'published_at')
    list_select_related = ('exercise',)
    list_filter = ('kind',)
    search_fields = ('exercise__title',)
    autocomplete_fields = ('exercise', 'sign', 'plate_a', 'plate_b')
    actions = ('publish', 'withdraw', 'make_draft')
    common_fields = ('exercise', 'kind', 'prompt', 'explanation', 'source_url', 'sign')
    published_fields = (*common_fields, 'plate_a', 'plate_b', 'answer_data', 'published_at', 'withdrawn_at')

    def get_fieldsets(self, request, obj=None):
        if obj and obj.published_at:
            return [(None, {'fields': self.published_fields})]
        return [
            (None, {'fields': self.common_fields}),
            ('Изображения к заданию', {'fields': ('new_images',)}),
            ('Порядок действий', {'fields': ('cards', 'orders')}),
            ('Знак и табличка', {
                'fields': ('plate_a', 'plate_b', 'meanings', 'conditions', 'right_meanings', 'right_a', 'right_b'),
                'description': 'Один вариант на строку. Верные номера идут через запятую, счёт с единицы.',
            }),
        ]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.published_at:
            return self.published_fields
        return ('exercise',) if obj else ()

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and (obj is None or not obj.published_at)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser and obj and not obj.published_at)

    def view_on_site(self, obj):
        return f'/practice/{obj.exercise.slug}/?preview={obj.pk}'

    def get_urls(self):
        return [
            path('<int:object_id>/make-draft/', self.admin_site.admin_view(self.make_draft_view),
                 name='app_practiceversion_make_draft'),
        ] + super().get_urls()

    def make_draft_view(self, request, object_id):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        if not self.has_add_permission(request):
            raise PermissionDenied
        source = get_object_or_404(PracticeVersion, pk=object_id, published_at__isnull=False)
        draft = copy_practice_version(source)
        self.log_addition(request, draft, 'Черновик создан на основе существующей версии.')
        self.message_user(request, 'Черновик создан. Измените его и опубликуйте новую версию.', messages.SUCCESS)
        return redirect('admin:app_practiceversion_change', draft.pk)

    @admin.display(description='Статус')
    def version_status(self, version):
        if version.withdrawn_at:
            return 'Отозвана'
        if version.exercise.published_version_id == version.pk:
            return 'На сайте'
        return 'Предыдущая' if version.published_at else 'Черновик'

    @admin.display(description='Карточки, варианты и верные ответы')
    def answer_data(self, version):
        groups = {
            'cards': 'Карточки', 'orders': 'Верные порядки',
            'meanings': 'Смысл знака', 'conditions': 'Условия',
            'right_meanings': 'Верный смысл', 'right_a': 'Верное условие А', 'right_b': 'Верное условие Б',
        }
        rows = format_html_join('', '<li><strong>{}</strong> — {}</li>', (
            (label, '; '.join(map(str, version.content[key]))) for key, label in groups.items() if key in version.content
        ))
        return format_html('<ul>{}</ul>', rows)

    @admin.action(description='Опубликовать выбранную версию')
    def publish(self, request, queryset):
        selection = list(queryset[:2])
        if len(selection) != 1:
            self.message_user(request, 'Для публикации выберите одну версию.', messages.ERROR)
            return
        version = selection[0]
        try:
            publish_practice(version.pk)
        except ValidationError as error:
            self.message_user(request, f'{version}. {" ".join(error.messages)}', messages.ERROR)
        else:
            self.log_change(request, version, 'Версия опубликована.')
            self.message_user(request, f'{version} опубликована.', messages.SUCCESS)

    @admin.action(description='Отозвать выбранные версии')
    def withdraw(self, request, queryset):
        for version in queryset.filter(published_at__isnull=False, withdrawn_at__isnull=True):
            withdraw_practice(version.pk)
            self.log_change(request, version, 'Версия отозвана.')
        self.message_user(request, 'Готово. Отозванные версии закрыты для прохождения.', messages.SUCCESS)

    @admin.action(description='Создать новые черновики на основе выбранных')
    def make_draft(self, request, queryset):
        for version in queryset:
            draft = copy_practice_version(version)
            self.log_addition(request, draft, 'Черновик создан на основе существующей версии.')
        self.message_user(request, 'Новые черновики доступны в списке версий.', messages.SUCCESS)


class NewsPostForm(forms.ModelForm):
    new_images = GalleryUploads()

    class Meta:
        model = NewsPost
        fields = '__all__'

    def clean_cover(self):
        return prepare_image(self.cleaned_data['cover'])


@admin.register(NewsPost)
class NewsPostAdmin(SlugEditorialAdmin):
    form = NewsPostForm
    inlines = (NewsImageInline,)
    list_display = ('title', 'kind', 'published_at', 'starts_at', 'cancelled')
    list_filter = ('kind', 'cancelled')
    search_fields = ('title', 'slug')
    autocomplete_fields = ('signs', 'exercises')
    readonly_fields = ('published_at', 'cover_preview')
    actions = ('publish', 'unpublish')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'kind', 'summary', 'body', 'published_at')}),
        ('Обложка и учебные материалы', {'fields': ('cover_preview', 'cover', 'cover_credit', 'signs', 'exercises')}),
        ('Фотографии в тексте новости', {'fields': ('new_images',)}),
        ('Поля анонса', {'fields': (
            'starts_at', 'timezone_name', 'venue', 'audience', 'organizer',
            'registration_deadline', 'registration_url', 'cancelled',
        )}),
    )

    def view_on_site(self, obj):
        return f'/news/{obj.slug}/' if obj.published_at else None

    @admin.display(description='Обложка')
    def cover_preview(self, obj):
        return image_preview(obj.cover)

    @admin.action(description='Опубликовать')
    @transaction.atomic
    def publish(self, request, queryset):
        for post in queryset.filter(published_at__isnull=True).order_by('pk').select_for_update():
            post.published_at = timezone.now()
            try:
                post.full_clean()
            except ValidationError as error:
                self.message_user(request, f'{post}. {" ".join(error.messages)}', messages.ERROR)
            else:
                post.save(update_fields=['published_at'])
                self.log_change(request, post, 'Опубликовано.')
                self.message_user(request, f'«{post}» опубликовано.', messages.SUCCESS)

    @admin.action(description='Снять с публикации')
    @transaction.atomic
    def unpublish(self, request, queryset):
        for post in queryset.exclude(published_at=None).order_by('pk').select_for_update():
            post.published_at = None
            post.save(update_fields=['published_at'])
            self.log_change(request, post, 'Снято с публикации.')
        self.message_user(request, 'Публикации сняты с сайта.', messages.SUCCESS)
