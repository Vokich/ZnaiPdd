from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models

from app.editorial.models import ContentImage
from app.signs.models import RoadSign


class PracticeExercise(models.Model):
    class Topic(models.TextChoices):
        CROSSING = 'crossing', 'Переход дороги'
        CYCLING = 'cycling', 'Велосипед'
        SIGNS = 'signs', 'Дорожные знаки'

    class Difficulty(models.TextChoices):
        BASIC = 'basic', 'Начальный'
        ADVANCED = 'advanced', 'Продвинутый'

    title = models.CharField('Название', max_length=150)
    slug = models.SlugField('Адрес задания', unique=True)
    topic = models.CharField('Тема', max_length=12, choices=Topic.choices)
    difficulty = models.CharField('Сложность', max_length=12, choices=Difficulty.choices)
    published_version = models.ForeignKey(
        'PracticeVersion', on_delete=models.SET_NULL, null=True, blank=True,
        editable=False, related_name='+',
    )

    class Meta:
        ordering = ['id']
        verbose_name = 'Задание по ПДД'
        verbose_name_plural = 'Задания по ПДД'

    def __str__(self):
        return self.title

    def clean(self):
        if self.slug == 'history':
            raise ValidationError({'slug': 'Этот адрес занят историей прохождений.'})


class PracticeVersion(models.Model):
    class Kind(models.TextChoices):
        ORDER = 'order', 'Порядок действий'
        PLATES = 'plates', 'Знак и табличка'

    exercise = models.ForeignKey(PracticeExercise, on_delete=models.CASCADE, related_name='versions', verbose_name='Задание')
    kind = models.CharField('Формат', max_length=8, choices=Kind.choices)
    prompt = models.TextField('Условие', max_length=1500)
    explanation = models.TextField('Объяснение', max_length=2000)
    source_url = models.URLField('Ссылка на пункт ПДД', max_length=500, validators=[URLValidator(schemes=['http', 'https'])])
    sign = models.ForeignKey(RoadSign, on_delete=models.PROTECT, null=True, blank=True, related_name='+', verbose_name='Знак')
    plate_a = models.ForeignKey(
        RoadSign, on_delete=models.PROTECT, null=True, blank=True, related_name='+',
        limit_choices_to={'category': RoadSign.Category.DOP_INFO}, verbose_name='Первая табличка',
    )
    plate_b = models.ForeignKey(
        RoadSign, on_delete=models.PROTECT, null=True, blank=True, related_name='+',
        limit_choices_to={'category': RoadSign.Category.DOP_INFO}, verbose_name='Вторая табличка',
    )
    content = models.JSONField(default=dict, editable=False)
    published_at = models.DateTimeField('Опубликована', null=True, blank=True, editable=False)
    withdrawn_at = models.DateTimeField('Отозвана', null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-id']
        verbose_name = 'Версия задания'
        verbose_name_plural = 'Версии заданий'

    def __str__(self):
        return f'{self.exercise} · № {self.pk}' if self.pk else str(self.exercise)


class PracticeResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='practice_results')
    version = models.ForeignKey(PracticeVersion, on_delete=models.PROTECT, related_name='results')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at', '-id']
        constraints = [models.UniqueConstraint(fields=['user', 'version'], name='unique_practice_completion')]
        verbose_name = 'Результат практики'
        verbose_name_plural = 'Результаты практики'


class PracticeImage(ContentImage):
    version = models.ForeignKey(PracticeVersion, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('Файл', upload_to='practice/')
