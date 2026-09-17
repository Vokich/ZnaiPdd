from django.db import models
from django.contrib.auth.models import User
from datetime import date

class Profile(models.Model):
    class Role(models.TextChoices):
        CHILD = 'child', 'Ребенок'
        TEACHER = 'teacher', 'Педагог'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CHILD,
        verbose_name='Роль'
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    surname1 = models.CharField(max_length=50, verbose_name='Фамилия')
    name = models.CharField(max_length=50, verbose_name='Имя')
    surname2 = models.CharField(max_length=50, blank=True, verbose_name='Отчество')
    school = models.CharField(max_length=100, verbose_name='Учебное заведение')
    birth_date = models.DateField(verbose_name='Дата рождения')
    region = models.CharField(max_length=400, verbose_name='Муниципалитет')
    position = models.CharField(max_length=100, blank=True, verbose_name='Должность')

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f"{self.surname1} {self.name}"

    @property
    def age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None
    @property
    def full_name(self):
      parts = [self.surname1, self.name]
      return ' '.join(parts)


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


class TeacherLessonReport(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_reports', verbose_name='Педагог')
  lesson_date = models.DateField(verbose_name='Дата проведения урока')
  location = models.CharField(max_length=300, verbose_name='Место проведения')
  children_count = models.PositiveIntegerField(verbose_name='Количество детей')
  children_list = models.TextField(verbose_name='Список детей',
                                   help_text='Введите имена детей через запятую или с новой строки')
  photo_link = models.URLField(verbose_name='Ссылка на фотоотчёт или группу', blank=True,
                               help_text='Ссылка на фотоальбом, облачное хранилище или группу в соцсетях')
  created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания отчёта')
  certificate_generated = models.BooleanField(default=False, verbose_name='Грамота сгенерирована')
  class Meta:
    verbose_name = 'Отчёт об уроке ПДД'
    verbose_name_plural = 'Отчёты об уроках ПДД'
    ordering = ['-lesson_date']

  def __str__(self):
    return f"{self.user.profile.full_name} - {self.lesson_date} ({self.children_count} чел.)"

  def get_children_list_as_array(self):
    import re
    items = re.split(r'[,\n;]+', self.children_list)
    return [item.strip() for item in items if item.strip()]

class Certificate(models.Model):
  class TestType(models.TextChoices):
    JUNIOR = 'junior', 'Младшая группа (8-12)'
    TEEN = 'teen', 'Подростковая группа (12-15)'
    ADULT = 'adult', 'Старшая группа (16-18)'

  class DocumentType(models.TextChoices):
    CERTIFICATE = 'certificate', 'Сертификат'
    DIPLOMA = 'diploma', 'Диплом'

  user = models.ForeignKey(User, on_delete=models.CASCADE)
  test_type = models.CharField(max_length=20, choices=TestResult.TestType.choices)
  document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.CERTIFICATE)
  test_result = models.ForeignKey(TestResult, on_delete=models.CASCADE)
  generated_at = models.DateTimeField(auto_now_add=True)
  download_count = models.IntegerField(default=0)

  class Meta:
    verbose_name = 'Сертификат'
    verbose_name_plural = 'Сертификаты'
    ordering = ['-generated_at']
    unique_together = ['user', 'test_type', 'document_type']

  def __str__(self):
    return f"{self.user.profile.full_name} - {self.get_test_type_display()}"


