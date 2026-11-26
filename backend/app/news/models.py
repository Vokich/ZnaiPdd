from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models

from app.editorial.models import ContentImage
from app.practice.models import PracticeExercise
from app.signs.models import RoadSign


class NewsPost(models.Model):
    class Kind(models.TextChoices):
        NEWS = 'news', 'Новость'
        EVENT = 'event', 'Анонс'
        RESULT = 'result', 'Итоги'

    TIMEZONES = (
        ('Europe/Moscow', 'Москва'), ('Europe/Kaliningrad', 'Калининград'),
        ('Europe/Samara', 'Самара'), ('Asia/Yekaterinburg', 'Екатеринбург'),
        ('Asia/Omsk', 'Омск'), ('Asia/Krasnoyarsk', 'Красноярск'), ('Asia/Irkutsk', 'Иркутск'),
        ('Asia/Yakutsk', 'Якутск'), ('Asia/Vladivostok', 'Владивосток'),
        ('Asia/Magadan', 'Магадан'), ('Asia/Kamchatka', 'Камчатка'),
    )
    title = models.CharField('Заголовок', max_length=160)
    slug = models.SlugField('Адрес публикации', unique=True)
    kind = models.CharField('Тип', max_length=8, choices=Kind.choices, default=Kind.NEWS)
    summary = models.CharField('Краткое описание', max_length=280, blank=True)
    body = models.TextField('Текст публикации', max_length=12000, blank=True)
    cover = models.ImageField('Обложка', upload_to='news/', blank=True)
    cover_credit = models.CharField('Источник обложки и условия использования', max_length=250, blank=True)
    signs = models.ManyToManyField(RoadSign, blank=True, verbose_name='Связанные знаки')
    exercises = models.ManyToManyField(PracticeExercise, blank=True, verbose_name='Связанные задания')
    published_at = models.DateTimeField('Опубликована', null=True, blank=True, editable=False)
    starts_at = models.DateTimeField('Начало (по Москве)', null=True, blank=True)
    timezone_name = models.CharField('Часовой пояс показа', max_length=24, choices=TIMEZONES, default='Europe/Moscow')
    venue = models.CharField('Место или онлайн-формат', max_length=200, blank=True)
    audience = models.CharField('Для кого', max_length=120, blank=True)
    organizer = models.CharField('Организатор', max_length=150, blank=True)
    registration_deadline = models.DateTimeField('Регистрация до (по Москве)', null=True, blank=True)
    registration_url = models.URLField('Внешняя ссылка для регистрации', max_length=500, blank=True,
                                       validators=[URLValidator(schemes=['https', 'http'])])
    cancelled = models.BooleanField('Мероприятие отменено', default=False)

    class Meta:
        ordering = ['-published_at', '-id']
        verbose_name = 'Публикация'
        verbose_name_plural = 'Новости и мероприятия'

    def __str__(self):
        return self.title

    def publication_errors(self):
        errors = {}
        if not self.body.strip():
            errors['body'] = 'Добавьте текст публикации.'
        if not self.summary.strip():
            errors['summary'] = 'Добавьте краткое описание.'
        if self.cover and not self.cover_credit.strip():
            errors['cover_credit'] = 'Укажите источник обложки и условия использования.'
        if self.kind == self.Kind.EVENT:
            for field in ('starts_at', 'venue', 'audience', 'organizer'):
                if not getattr(self, field):
                    errors[field] = 'Заполните это поле для анонса.'
            if self.registration_deadline and not self.registration_url:
                errors['registration_url'] = 'Добавьте ссылку, если указан срок регистрации.'
            elif self.registration_deadline and self.starts_at and self.registration_deadline > self.starts_at:
                errors['registration_deadline'] = 'Срок регистрации должен быть до начала встречи.'
        return errors

    def clean(self):
        if self.slug == 'next':
            raise ValidationError({'slug': 'Этот адрес занят блоком ближайшего мероприятия.'})
        if self.published_at and (errors := self.publication_errors()):
            raise ValidationError(errors)


class NewsImage(ContentImage):
    post = models.ForeignKey(NewsPost, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('Файл', upload_to='news/gallery/')
