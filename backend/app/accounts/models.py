from datetime import date

from django.contrib.auth.models import User
from django.core.validators import URLValidator
from django.db import models

from app.organizations.models import Municipality, Organization


class Profile(models.Model):
    class Role(models.TextChoices):
        CHILD = 'child', 'Пользователь'
        TEACHER = 'teacher', 'Педагог'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        blank=True,
        verbose_name='Роль'
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    surname1 = models.CharField(max_length=50, blank=True, verbose_name='Фамилия')
    name = models.CharField(max_length=50, blank=True, verbose_name='Имя')
    surname2 = models.CharField(max_length=50, blank=True, verbose_name='Отчество')
    school = models.CharField(max_length=100, blank=True, verbose_name='Прежнее название учебного заведения')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    region = models.CharField(max_length=400, blank=True, verbose_name='Прежнее название муниципалитета')
    position = models.CharField(max_length=100, blank=True, verbose_name='Должность')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Организация')
    municipality = models.ForeignKey(Municipality, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Муниципалитет')
    organization_confirmed = models.BooleanField('Организация подтверждена администратором', default=False)
    competition_enabled = models.BooleanField('Участвует в рейтинге', default=False)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return self.full_name or self.user.get_username()

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
        return ' '.join(filter(None, (self.surname1, self.name)))


class TeacherContact(models.Model):
    label = models.CharField('Название ссылки', max_length=100)
    url = models.URLField('Ссылка', blank=True, validators=[URLValidator(schemes=['https', 'http'])])
    direct = models.BooleanField('Личные сообщения администратору', default=False)

    class Meta:
        verbose_name = 'Контакт для педагогов'
        verbose_name_plural = 'Контакты для педагогов'
        ordering = ['-direct', 'pk']

    def __str__(self):
        return self.label
