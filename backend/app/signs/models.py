from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
from django.db import models
from django.templatetags.static import static

from app.signs.starter import STARTER_NUMBERS


class RoadSign(models.Model):
    class Category(models.TextChoices):
        WARNING = 'warning', 'Предупреждающие'
        PROHIBITING = 'prohibiting', 'Запрещающие'
        MANDATORY = 'mandatory', 'Предписывающие'
        SPECIAL_MANDATORY = 'special_mandatory', 'Особых предписаний'
        INFO = 'info', 'Информационные'
        DOP_INFO = 'dop_info', 'Дополнительной информации'
        SERVICE = 'service', 'Знаки сервиса'
        PRIORITET = 'prioritet', 'Приоритета'


    name = models.CharField('Название', max_length=200)
    slug = models.SlugField(unique=True)
    number = models.CharField(
        'Номер по ПДД', max_length=16, blank=True,
        validators=[RegexValidator(r'^[1-8](?:\.[0-9]+){1,3}$', 'Укажите номер знака, например 5.19.1.')],
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    image = models.ImageField('Изображение', upload_to='signs/', blank=True)
    source_url = models.URLField(
        'Ссылка на правило', max_length=500, blank=True, validators=[URLValidator(schemes=['http', 'https'])],
    )
    image_credit = models.CharField('Источник изображения и условия использования', max_length=300, blank=True)
    reviewed_on = models.DateField('Дата проверки карточки', null=True, blank=True)
    is_published = models.BooleanField('Опубликован', default=False)
    short_description = models.TextField('Краткое описание')
    full_description = models.TextField('Полное описание', blank=True)
    fun_fact = models.TextField('Интересный факт', blank=True)
    question = models.TextField('Вопрос для теста', blank=True)
    answer_options = models.JSONField('Варианты ответов', default=list, blank=True)
    correct_answer = models.IntegerField('Номер правильного ответа', default=1)
    order = models.IntegerField('Порядок', default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Знак ПДД'
        verbose_name_plural = 'Знаки ПДД'
        constraints = [
            models.UniqueConstraint(fields=['number'], condition=~models.Q(number=''), name='road_sign_number_unique'),
        ]

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        if self.number in STARTER_NUMBERS:
            return static(f'road-signs/{self.number}.png')
        return None

    @property
    def has_test(self):
        options = self.answer_options
        return (
            bool(self.question.strip())
            and isinstance(options, list)
            and len(options) >= 2
            and all(isinstance(option, str) and option.strip() for option in options)
            and len({option.strip().casefold() for option in options}) == len(options)
            and isinstance(self.correct_answer, int)
            and 1 <= self.correct_answer <= len(options)
        )

    def clean(self):
        if self.answer_options is None:
            self.answer_options = []
        if not self.is_published:
            return
        errors = {}
        if not self.number:
            errors['number'] = 'Укажите номер опубликованного знака.'
        if not (self.short_description.strip() or self.full_description.strip()):
            errors['short_description'] = 'Добавьте описание знака.'
        if not self.source_url:
            errors['source_url'] = 'Укажите ссылку на правило.'
        if not self.reviewed_on:
            errors['reviewed_on'] = 'Укажите дату проверки карточки.'
        if not self.image_url:
            errors['image'] = 'Добавьте изображение знака.'
        if self.image and not self.image_credit.strip():
            errors['image_credit'] = 'Укажите источник загруженного изображения.'
        if (self.question or self.answer_options) and not self.has_test:
            errors['answer_options'] = 'Для мини-теста нужны вопрос, разные варианты ответа и номер верного варианта.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class UserSignProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sign_progress')
    sign = models.ForeignKey(RoadSign, on_delete=models.CASCADE)
    unlocked = models.BooleanField(default=False)
    test_passed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'sign']
        verbose_name = 'Прогресс по знаку'
        verbose_name_plural = 'Прогресс по знакам'

    def __str__(self):
        return f'{self.user.username} — {self.sign.name}'
