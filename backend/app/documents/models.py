from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from app.quizzes.models import TestResult


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

  def clean(self):
    if self.test_result_id and (self.test_result.user_id != self.user_id or self.test_result.test_type != self.test_type):
      raise ValidationError({'test_result': 'Результат должен относиться к владельцу и типу теста этого документа.'})
    if self.test_result_id:
      result = self.test_result
      expected = self.DocumentType.DIPLOMA if result.earns_diploma else self.DocumentType.CERTIFICATE
      if not result.passed or result.score < result.passing_score:
        raise ValidationError({'test_result': 'Для выдачи документа нужен успешно пройденный тест.'})
      if self.document_type != expected:
        raise ValidationError({'document_type': 'Вид документа должен соответствовать результату.'})

  def __str__(self):
    return f'{self.user.get_username()} — {self.get_test_type_display()}'
