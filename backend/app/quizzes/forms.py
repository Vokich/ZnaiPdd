import json
from math import ceil

from django import forms
from django.core.exceptions import ValidationError
from django.utils.crypto import salted_hmac

from app.models import AgeTestQuestion, TestResult


class AgePddTestForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        rows = AgeTestQuestion.objects.filter(test_type=self.test_type).values_list(
            'number', 'text', 'options', 'correct',
        )
        self.questions_data = [
            {'id': number, 'text': text, 'options': options, 'correct': correct}
            for number, text, options, correct in rows
        ]
        self.passing_score = ceil(len(self.questions_data) * 3 / 5)
        self.revision = salted_hmac(
            'age-test.' + self.test_type, json.dumps(self.questions_data, ensure_ascii=False),
        ).hexdigest()
        for question in self.questions_data:
            self.fields[f'question_{question["id"]}'] = forms.ChoiceField(
                label=question['text'],
                choices=enumerate(question['options'], 1),
                widget=forms.RadioSelect(attrs={'class': 'radio-option'}),
                error_messages={'required': 'Выберите ответ на этот вопрос'},
            )

    def clean(self):
        values = super().clean()
        if not self.questions_data:
            raise ValidationError('В этом тесте пока нет вопросов.')
        return values

    def check_answers(self, passing_score=None):
        if passing_score is None:
            passing_score = self.passing_score
        results = {}
        for question in self.questions_data:
            number = question['id']
            answer = int(self.cleaned_data[f'question_{number}'])
            results[number] = {
                'question': question['text'],
                'user_answer': answer,
                'correct_answer': question['correct'],
                'is_correct': answer == question['correct'],
            }
        score = sum(item['is_correct'] for item in results.values())
        return {
            'score': score,
            'total': len(results),
            'passing_score': passing_score,
            'passed': bool(results) and score >= passing_score,
            'results': results,
        }


class JuniorPddTestForm(AgePddTestForm):
    test_type = TestResult.TestType.JUNIOR


class TeenPddTestForm(AgePddTestForm):
    test_type = TestResult.TestType.TEEN


class AdultPddTestForm(AgePddTestForm):
    test_type = TestResult.TestType.ADULT
