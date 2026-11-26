from django.db import models


class ContentImage(models.Model):
    alt = models.CharField('Описание для скринридера', max_length=200, blank=True)
    caption = models.CharField('Подпись под изображением', max_length=250, blank=True)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        abstract = True
        ordering = ['order', 'pk']
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'

    def __str__(self):
        return self.caption or self.alt or 'Изображение'
