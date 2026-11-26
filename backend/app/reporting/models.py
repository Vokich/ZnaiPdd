from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class PlatformAttempt(models.Model):
    class Kind(models.TextChoices):
        AGE = 'age', 'Возрастной тест'
        SIGN = 'sign', 'Мини-тест по знаку'
        PRACTICE = 'practice', 'Практика'
        ROUTE = 'route', 'Безопасный маршрут'
        QR = 'qr', 'QR-тест платформы'
        LESSON = 'lesson', 'Задание на общем экране'

    kind = models.CharField('Раздел', max_length=12, choices=Kind.choices)
    task = models.CharField('Код задания', max_length=180)
    title = models.CharField('Задание', max_length=300)
    version = models.CharField('Версия', max_length=80, blank=True)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE, verbose_name='Участник')
    organization = models.CharField('Организация при прохождении', max_length=300, blank=True)
    source = models.CharField(max_length=120, unique=True, null=True, editable=False)
    completed_at = models.DateTimeField('Дата', default=timezone.now)
    score = models.IntegerField('Баллы')
    total = models.PositiveIntegerField('Максимум за попытку')
    answers = models.JSONField('Ответы', default=list)

    class Meta:
        verbose_name = 'Попытка по заданию платформы'
        verbose_name_plural = 'Статистика заданий платформы'
        ordering = ['-completed_at', '-pk']
        indexes = [models.Index(fields=['user', 'kind', 'task', '-score'], name='platform_user_task_score')]

    def __str__(self):
        return self.title
