import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from app.organizations.models import Organization
from app.routes.levels import LEVELS


class ClassroomQuiz(models.Model):
    owner = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    instruction = models.TextField(blank=True)
    questions = models.JSONField(default=list)
    revision = models.PositiveIntegerField(default=1)
    ready = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class ClassroomVersion(models.Model):
    quiz = models.ForeignKey(ClassroomQuiz, on_delete=models.CASCADE, related_name='versions')
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=160)
    instruction = models.TextField(blank=True)
    questions = models.JSONField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['quiz', 'number'], name='class_quiz_version_uniq')]


class ClassroomRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.SlugField(blank=True)
    version = models.ForeignKey(ClassroomVersion, null=True, on_delete=models.PROTECT)
    code = models.CharField(max_length=8, unique=True, null=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    deadline = models.DateTimeField(null=True, db_index=True)
    accepting = models.BooleanField(default=True)
    closed_at = models.DateTimeField(null=True)
    review_until = models.DateTimeField(null=True)
    summary = models.JSONField(default=dict)


class ClassroomAttempt(models.Model):
    run = models.ForeignKey(ClassroomRun, on_delete=models.CASCADE, related_name='attempts')
    participant = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    browser = models.CharField(max_length=64)
    started = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=0)
    answers = models.JSONField(default=list)
    score = models.PositiveSmallIntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'browser'], name='class_attempt_browser_uniq')]


class TeacherLessonReport(models.Model):
    classroom = models.OneToOneField(ClassroomRun, null=True, blank=True, on_delete=models.PROTECT, related_name='report')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=False, related_name='lesson_reports', verbose_name='Педагог')
    lesson_date = models.DateField(verbose_name='Дата проведения урока')
    location = models.CharField(max_length=300, blank=True, verbose_name='Площадка или кабинет')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Организация')
    participants_count = models.PositiveIntegerField(verbose_name='Количество участников')
    route_level = models.CharField(
        'Уровень безопасного маршрута', max_length=16, blank=True,
        choices=[(key, level['title']) for key, level in LEVELS.items()],
        help_text='Оставьте пустым для урока без маршрута.',
    )
    practice = models.ForeignKey(
        'PracticeExercise', on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='Задание из практики', related_name='lesson_reports',
    )
    completed_count = models.PositiveIntegerField('Сколько участников завершили задание', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания отчёта')
    certificate_generated = models.BooleanField(default=False, verbose_name='Грамота сгенерирована')

    class Meta:
        verbose_name = 'Отчёт об уроке ПДД'
        verbose_name_plural = 'Отчёты об уроках ПДД'
        ordering = ['-lesson_date', '-pk']
        indexes = [models.Index(fields=['user', '-lesson_date', '-id'], name='report_owner_date_idx')]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(route_level='', practice__isnull=True, completed_count__isnull=True)
                    | models.Q(classroom__isnull=False, route_level='', practice__isnull=True,
                               completed_count__lte=models.F('participants_count'))
                    | models.Q(classroom__isnull=True, route_level__in=tuple(LEVELS), practice__isnull=True, completed_count__isnull=False,
                               completed_count__lte=models.F('participants_count'))
                    | models.Q(classroom__isnull=True, route_level='', practice__isnull=False, completed_count__isnull=False,
                               completed_count__lte=models.F('participants_count'))
                ),
                name='lesson_route_completion_consistent',
            ),
        ]

    def clean(self):
        if self.classroom_id and (self.route_level or self.practice_id):
            raise ValidationError('Отчёт уже привязан к занятию.')
        if self.route_level and self.practice_id:
            raise ValidationError({'practice': 'Выберите одно задание для отчёта.'})
        with_activity = bool(self.route_level or self.practice_id)
        qr = self.classroom_id and self.classroom.version_id
        if not with_activity and not qr and self.completed_count is not None:
            raise ValidationError({'completed_count': 'Укажите количество завершивших только для урока с заданием.'})
        if with_activity and self.completed_count is None:
            raise ValidationError({'completed_count': 'Укажите, сколько участников завершили задание. Если никто, укажите 0.'})
        if self.completed_count is not None and self.participants_count is not None:
            if self.completed_count > self.participants_count:
                raise ValidationError({'completed_count': 'Завершивших не может быть больше, чем участников урока.'})

    def __str__(self):
        return f'{self.user.get_username()} — {self.lesson_date} ({self.participants_count} чел.)'
