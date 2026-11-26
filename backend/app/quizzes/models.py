from math import ceil

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class TestResult(models.Model):
    class TestType(models.TextChoices):
        JUNIOR = 'junior', 'Младшая группа'
        TEEN = 'teen', 'Подростковая группа'
        ADULT = 'adult', 'Взрослые'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results', verbose_name='Пользователь')
    test_type = models.CharField(max_length=10, choices=TestType.choices, verbose_name='Тип теста')
    score = models.IntegerField(verbose_name='Набранные баллы')
    total_questions = models.IntegerField(verbose_name='Всего вопросов')
    passing_score = models.IntegerField(verbose_name='Проходной балл')
    passed = models.BooleanField(default=False, verbose_name='Тест пройден')
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата завершения')

    class Meta:
        verbose_name = 'Результат теста'
        verbose_name_plural = 'Результаты тестов'
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_test_type_display()} ({self.score}/{self.total_questions})"

    @staticmethod
    def diploma_threshold(total):
        return ceil(total * 4 / 5)

    @property
    def earns_diploma(self):
        return self.passed and self.total_questions > 0 and self.score >= self.diploma_threshold(self.total_questions)


class AgeTestQuestion(models.Model):
    test_type = models.CharField('Возрастная группа', max_length=10, choices=TestResult.TestType.choices)
    number = models.PositiveIntegerField('Номер вопроса', validators=[MinValueValidator(1)])
    text = models.TextField('Вопрос')
    options = models.JSONField('Варианты ответа')
    correct = models.PositiveIntegerField('Номер правильного варианта', validators=[MinValueValidator(1)])
    reference = models.CharField('Пункт ПДД РФ или другого российского нормативного акта', max_length=220)

    class Meta:
        verbose_name = 'Вопрос возрастного теста'
        verbose_name_plural = 'Вопросы возрастных тестов'
        ordering = ['test_type', 'number']
        constraints = [
            models.UniqueConstraint(fields=['test_type', 'number'], name='age_test_question_number_uniq'),
        ]

    def __str__(self):
        return f'{self.get_test_type_display()} · {self.number}. {self.text}'

    def clean(self):
        super().clean()
        if not isinstance(self.options, list) or len(self.options) < 2:
            raise ValidationError({'options': 'Укажите как минимум два варианта ответа.'})
        if any(not isinstance(option, str) or not option.strip() for option in self.options):
            raise ValidationError({'options': 'Каждый вариант должен содержать текст.'})
        if len({option.strip().casefold() for option in self.options}) != len(self.options):
            raise ValidationError({'options': 'Варианты ответа должны различаться.'})
        if self.correct is not None and not 1 <= self.correct <= len(self.options):
            raise ValidationError({'correct': 'Укажите номер одного из вариантов, начиная с 1.'})
