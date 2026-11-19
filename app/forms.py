import json
from math import ceil

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.crypto import salted_hmac
from .models import AgeTestQuestion, Organization, Profile, TeacherLessonReport, TestResult


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label='Пароль', strip=False, widget=forms.PasswordInput)
    surname1 = forms.CharField(label='Фамилия', max_length=50)
    name = forms.CharField(label='Имя', max_length=50)
    surname2 = forms.CharField(label='Отчество (при наличии)', max_length=50, required=False)
    consent = forms.BooleanField(label='Согласие на обработку персональных данных')

    class Meta:
        model = User
        fields = ['username', 'password', 'surname1', 'name', 'surname2', 'email', 'consent']
        labels = {'username': 'Логин', 'email': 'Почта'}

    def clean_email(self):
        email = self.cleaned_data['email']
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с такой почтой уже существует.')
        return email

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error('password', error)

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                role=Profile.Role.CHILD,
                surname1=self.cleaned_data['surname1'],
                name=self.cleaned_data['name'],
                surname2=self.cleaned_data['surname2'],
            )
        return user


class LoginForm(forms.Form):
    username = forms.CharField(
        label='Логин',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='Пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


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


class TeacherLessonReportForm(forms.ModelForm):
    participants_count = forms.IntegerField(label='Количество участников', min_value=1, max_value=2147483647)

    class Meta:
        model = TeacherLessonReport
        fields = ['lesson_date', 'organization', 'location', 'participants_count', 'route_level', 'practice', 'completed_count']
        widgets = {'lesson_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        from .practice import public_exercises

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


class UserProfileForm(forms.ModelForm):
    surname1 = forms.CharField(label='Фамилия', max_length=50)
    name = forms.CharField(label='Имя', max_length=50)
    surname2 = forms.CharField(label='Отчество (при наличии)', max_length=50, required=False)
    organization = forms.ModelChoiceField(label='Организация', queryset=Organization.objects.select_related('municipality'), required=False)
    position = forms.CharField(label='Должность', max_length=100, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'surname1', 'name', 'surname2', 'organization', 'position']
        labels = {'username': 'Логин', 'email': 'Почта'}

    def __init__(self, *args, profile_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile_instance or Profile(user=self.instance)
        self.profile_fields = ['surname1', 'name', 'surname2', 'organization']
        if self.profile.role == Profile.Role.TEACHER:
            self.profile_fields.append('position')
        else:
            del self.fields['position']
        for field in self.profile_fields:
            self.initial[field] = getattr(self.profile, field)

    def clean_email(self):
        email = self.cleaned_data['email']
        if email and email != self.initial.get('email') and User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise ValidationError('Пользователь с такой почтой уже существует.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save(update_fields=['username', 'email'])
            for field in self.profile_fields:
                setattr(self.profile, field, self.cleaned_data[field])
            changed_fields = list(self.profile_fields)
            if not self.profile.role:
                self.profile.role = Profile.Role.CHILD
                changed_fields.append('role')
            if self.profile.pk:
                self.profile.save(update_fields=changed_fields)
            else:
                self.profile.save()
        return user


class PasswordChangeForm(forms.Form):
  old_password = forms.CharField(
    label='Текущий пароль',
    strip=False,
    widget=forms.PasswordInput(attrs={'class': 'form-control'})
  )
  new_password = forms.CharField(
    label='Новый пароль',
    strip=False,
    widget=forms.PasswordInput(attrs={'class': 'form-control'})
  )
  confirm_password = forms.CharField(
    label='Подтвердите новый пароль',
    strip=False,
    widget=forms.PasswordInput(attrs={'class': 'form-control'})
  )

  def __init__(self, *args, **kwargs):
    self.user = kwargs.pop('user', None)
    super().__init__(*args, **kwargs)

  def clean_old_password(self):
    old_password = self.cleaned_data.get('old_password')
    if self.user and not self.user.check_password(old_password):
      raise ValidationError("Неверный текущий пароль")
    return old_password

  def clean(self):
    cleaned_data = super().clean()
    new_password = cleaned_data.get('new_password')
    confirm_password = cleaned_data.get('confirm_password')
    if new_password and confirm_password and new_password != confirm_password:
      self.add_error('confirm_password', 'Пароли не совпадают')
    if new_password:
      try:
        validate_password(new_password, self.user)
      except ValidationError as error:
        self.add_error('new_password', error)
    return cleaned_data

  def save(self):
    self.user.set_password(self.cleaned_data['new_password'])
    self.user.save(update_fields=['password'])
    return self.user
