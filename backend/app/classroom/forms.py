from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from app.models import TeacherLessonReport
from app.practice.service import public_exercises
from app.routes.levels import published_levels


class TeacherLessonReportForm(forms.ModelForm):
    participants_count = forms.IntegerField(label='Количество участников', min_value=1, max_value=2147483647)

    class Meta:
        model = TeacherLessonReport
        fields = ['lesson_date', 'organization', 'location', 'participants_count', 'route_level', 'practice', 'completed_count']
        widgets = {'lesson_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['route_level'].choices = [
            ('', '---------'), *((key, level['title']) for key, level in published_levels().items()),
        ]

        self.fields['practice'].queryset = self.fields['practice'].queryset.filter(
            Q(pk__in=public_exercises().values('pk')) | Q(pk=self.instance.practice_id),
        )

    def clean(self):
        data = super().clean()
        if 'children_list' in self.data or 'photo_link' in self.data:
            raise ValidationError('Списки детей и ссылки на фото не принимаются.')
        if 'organization' in data and 'location' in data and not (data['organization'] or data['location']):
            self.add_error('location', 'Выберите организацию или укажите место проведения.')
        return data
