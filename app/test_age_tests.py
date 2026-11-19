from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import AgeTestQuestion, Profile, TestResult


class AgeTestBankTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pupil = User.objects.create_user('age-test-pupil')
        Profile.objects.create(user=cls.pupil, role=Profile.Role.CHILD)
        cls.editor = User.objects.create_superuser('age-test-editor')

    def test_starter_groups_and_previously_incorrect_keys(self):
        for group in TestResult.TestType.values:
            questions = AgeTestQuestion.objects.filter(test_type=group)
            self.assertEqual(list(questions.values_list('number', flat=True)), list(range(1, 31)))
            for question in questions:
                question.full_clean()
        for group, number, correct in [
            ('adult', 10, 2), ('adult', 12, 3), ('adult', 20, 2), ('adult', 25, 2),
            ('adult', 27, 3), ('teen', 30, 2),
        ]:
            self.assertEqual(AgeTestQuestion.objects.get(test_type=group, number=number).correct, correct)
        speed = AgeTestQuestion.objects.get(test_type='adult', number=20)
        self.assertEqual(speed.options[speed.correct - 1], '20 км/ч')

    def test_admin_edit_updates_both_clients_and_scoring(self):
        client = APIClient()
        client.force_login(self.pupil)
        quiz_url = '/api/tests/adult/'
        post_url = quiz_url + 'results/'
        original = client.get(quiz_url).json()
        question = AgeTestQuestion.objects.get(test_type='adult', number=20)
        url = reverse('admin:app_agetestquestion_change', args=[question.pk])
        self.client.force_login(self.editor)
        edit = dict(test_type='adult', number=20, text='Предел скорости по п. 10.2?',
                    options='20 км/ч\n10 км/ч', correct=3, reference=question.reference, _save=1)
        self.assertContains(self.client.post(url, edit), 'Укажите номер одного из вариантов')
        question.refresh_from_db()
        self.assertEqual(question.correct, 2)
        edit['correct'] = 1
        self.assertEqual(self.client.post(url, edit).status_code, 302)

        answers = dict(AgeTestQuestion.objects.filter(test_type='adult').values_list('number', 'correct'))
        self.assertEqual(client.post(post_url, {'answers': answers}, format='json').status_code, 409)
        quiz = client.get(quiz_url).json()
        self.assertEqual(quiz['questions'][19], {
            'id': 20, 'text': edit['text'], 'options': ['20 км/ч', '10 км/ч'],
        })
        stale = client.post(post_url, {'answers': answers, 'revision': original['revision']}, format='json')
        self.assertEqual(stale.status_code, 409)
        page = client.post('/age/adults/', {'revision': original['revision']})
        self.assertContains(page, 'Вопросы изменились', status_code=409)
        self.assertContains(page, edit['text'], status_code=409)
        self.assertFalse(TestResult.objects.exists())
        result = client.post(post_url, {'answers': answers, 'revision': quiz['revision']}, format='json')
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()['score'], 30)
        self.assertTrue(result.json()['earns_diploma'])

    def test_shortened_test_uses_same_award_percentages_in_html_and_pdf(self):
        AgeTestQuestion.objects.filter(test_type='junior', number__gt=5).delete()
        client = APIClient()
        client.force_login(self.pupil)
        page = client.get('/age/child/')
        quiz = page.context['form']
        self.assertEqual(quiz.passing_score, 3)
        answers = {f'question_{q["id"]}': q['correct'] for q in quiz.questions_data}
        last = quiz.questions_data[-1]
        answers[f'question_{last["id"]}'] = last['correct'] % len(last['options']) + 1
        submitted = client.post('/age/child/', {**answers, 'revision': quiz.revision}, follow=True)
        self.assertContains(submitted, 'Скачать Диплом')
        result = TestResult.objects.get()
        self.assertEqual((result.score, result.total_questions, result.passing_score), (4, 5, 3))
        self.assertEqual(client.get('/api/tests/junior/certificate/').status_code, 200)
        self.assertEqual(self.pupil.certificate_set.get().document_type, 'diploma')

    def test_empty_group_does_not_create_a_result(self):
        AgeTestQuestion.objects.filter(test_type='teen').delete()
        client = APIClient()
        client.force_login(self.pupil)
        self.assertEqual(client.get('/api/tests/teen/').status_code, 404)
        self.assertContains(client.get('/age/teen/'), 'пока нет вопросов', status_code=404)
        response = client.post('/api/tests/teen/results/', {'answers': {}}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(TestResult.objects.exists())
