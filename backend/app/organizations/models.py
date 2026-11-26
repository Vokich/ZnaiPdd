from django.db import models


class Municipality(models.Model):
    code = models.CharField('Код ОКТМО', max_length=8, primary_key=True)
    name = models.CharField('Муниципалитет', max_length=400)

    class Meta:
        ordering = ['name', 'code']
        verbose_name = 'Муниципалитет'
        verbose_name_plural = 'Муниципалитеты'

    def __str__(self):
        return self.name


class Organization(models.Model):
    name = models.CharField('Название', max_length=300)
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT, verbose_name='Муниципалитет')

    class Meta:
        ordering = ['name', 'pk']
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'
        constraints = [models.UniqueConstraint(fields=['municipality', 'name'], name='organization_municipality_name_uniq')]

    def __str__(self):
        return f'{self.name} ({self.municipality})'
