from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class RouteSceneContent(models.Model):
    pool = models.CharField('Группа ситуаций', max_length=5, blank=True, choices=[('walk', 'Пешком'), ('bike', 'На велосипеде')])
    key = models.SlugField('Код ситуации', primary_key=True)
    title = models.CharField('Название', max_length=150)
    prompt = models.TextField('Ситуация')
    rule = models.CharField('Пункт правил', max_length=120, blank=True)
    url = models.URLField('Ссылка на правило', max_length=500, blank=True)
    choices = models.JSONField('Действия')

    class Meta:
        verbose_name = 'Ситуация маршрута'
        verbose_name_plural = 'Ситуации маршрутов'
        ordering = ['title']

    def __str__(self):
        return self.title


class RouteProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='route_progress')
    state = models.JSONField()


class RouteResult(models.Model):
    attempt = models.CharField(max_length=32, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='route_results', db_index=False, verbose_name='Пользователь')
    level = models.CharField(max_length=16)
    score = models.IntegerField('Баллы')
    total = models.PositiveSmallIntegerField()
    mistakes = models.PositiveIntegerField('Ошибки')
    rule_reviews = models.JSONField(default=list)
    completed_at = models.DateTimeField('Дата прохождения', auto_now_add=True)

    class Meta:
        verbose_name = 'Результат маршрута'
        verbose_name_plural = 'Результаты маршрутов'
        indexes = [models.Index(fields=['user', 'level', '-score'], name='route_user_level_score_idx')]

    def __str__(self):
        return f'{self.user.get_username()} — {self.score}/{self.total}'

    def clean(self):
        if isinstance(self.score, int) and isinstance(self.total, int) and self.score > self.total:
            raise ValidationError({'score': 'Баллы не могут превышать максимум за маршрут.'})
