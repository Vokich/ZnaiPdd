from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .forms import JuniorPddTestForm
from .models import Certificate, Profile, RoadSign, TestResult


class SessionApiTests(TestCase):
    registration = {
        'username': 'student',
        'password': 'test-password',
        'email': 'student@example.com',
        'surname1': 'Иванов',
        'name': 'Иван',
        'school': 'Школа',
        'birth_date': '2010-01-01',
        'region': 'город Елец, Липецкая область',
        'role': 'child',
        'consent': True,
    }

    def test_registration_login_and_logout_enforce_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/users/', self.registration, format='json').status_code, 403)
        self.assertEqual(client.post('/api/session/', {}, format='json').status_code, 403)
        self.assertEqual(client.get('/api/session/').json(), {'user': None})

        def csrf():
            return {'HTTP_X_CSRFTOKEN': client.cookies['csrftoken'].value}

        response = client.post('/api/users/', {**self.registration, 'consent': False}, format='json', **csrf())
        self.assertEqual(response.status_code, 400)
        self.assertIn('consent', response.json())
        response = client.post('/api/users/', {**self.registration, 'birth_date': 2010}, format='json', **csrf())
        self.assertEqual(response.status_code, 400)
        self.assertIn('birth_date', response.json())
        response = client.post('/api/users/', self.registration, format='json', **csrf())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['role'], Profile.Role.CHILD)
        self.assertEqual(client.get('/api/profile/').json()['profile']['region'], self.registration['region'])
        self.assertEqual(client.delete('/api/session/', **csrf()).status_code, 204)
        self.assertEqual(client.get('/api/profile/').status_code, 403)

        credentials = {key: self.registration[key] for key in ('username', 'password')}
        response = client.post('/api/session/', credentials, format='json', **csrf())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['username'], 'student')
        self.assertEqual(client.get('/api/session/').json()['user']['username'], 'student')

    def test_profile_preserves_a_legacy_municipality_on_partial_update(self):
        user = User.objects.create_user(username='legacy', email='legacy@example.com')
        user.profile.role = Profile.Role.CHILD
        user.profile.region = 'Старое название'
        user.profile.save(update_fields=['role', 'region'])
        client = APIClient()
        client.force_login(user)
        response = client.patch('/api/profile/', {'name': 'Новое имя', 'role': 'teacher'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['profile']['name'], 'Новое имя')
        self.assertEqual(response.json()['profile']['region'], 'Старое название')
        self.assertEqual(response.json()['profile']['role'], Profile.Role.CHILD)


class LearningApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username='student')
        Profile.objects.filter(user=self.student).update(role=Profile.Role.CHILD)
        self.teacher = User.objects.create_user(username='teacher')

    def test_quiz_scores_server_side_and_issues_pdf_for_own_result(self):
        self.client.force_login(self.student)
        quiz = self.client.get('/api/tests/junior/').json()
        self.assertEqual(len(quiz['questions']), 30)
        self.assertNotIn('correct', quiz['questions'][0])
        answers = {str(question['id']): question['correct'] for question in JuniorPddTestForm().questions_data}
        url = '/api/tests/junior/results/'
        self.assertEqual(self.client.post(url, {'answers': {}}, format='json').status_code, 400)
        result = self.client.post(url, {'answers': answers}, format='json')
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()['score'], 30)
        result_id = result.json()['id']
        self.assertEqual(self.client.get(f'{url}?id={result_id}').json()['id'], result_id)
        download = self.client.get(f'/api/tests/junior/certificate/?id={result_id}')
        self.assertEqual(download.status_code, 200)
        self.assertTrue(b''.join(download.streaming_content).startswith(b'%PDF'))
        self.assertEqual(Certificate.objects.get(user=self.student).document_type, Certificate.DocumentType.DIPLOMA)

        other = User.objects.create_user(username='other')
        Profile.objects.filter(user=other).update(role=Profile.Role.CHILD)
        self.client.force_login(other)
        self.assertEqual(self.client.get(f'{url}?id={result_id}').status_code, 404)
        self.assertEqual(self.client.get(f'/api/tests/junior/certificate/?id={result_id}').status_code, 404)
        self.assertEqual(TestResult.objects.count(), 1)

    def test_roles_and_report_ownership(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get('/api/lesson-reports/').status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get('/api/tests/teen/').status_code, 403)
        response = self.client.post('/api/lesson-reports/', {
            'lesson_date': '2025-09-01',
            'location': 'Школа',
            'children_count': 2,
            'children_list': 'Иван, Мария',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.client.get('/api/lesson-reports/').json()), 1)
        self.client.force_login(User.objects.create_user(username='another-teacher'))
        self.assertEqual(self.client.get('/api/lesson-reports/').json(), [])

    def test_sign_remains_locked_until_correct_answer(self):
        sign = RoadSign.objects.create(
            slug='crosswalk', name='Пешеходный переход', category=RoadSign.Category.INFO,
            image='signs/crosswalk.png', short_description='Переход',
            question='Что здесь?', answer_options=['Переход', 'Остановка'], correct_answer=1,
        )
        self.client.force_login(self.student)
        url = f'/api/signs/{sign.slug}/'
        self.assertIsNone(self.client.get(url).json()['image'])
        quiz = self.client.get(url + 'test/').json()
        self.assertEqual({option['id'] for option in quiz['options']}, {1, 2})
        self.assertNotIn('correct_answer', quiz)
        self.assertEqual(self.client.post(url + 'test/', {'answer': 2}, format='json').status_code, 400)
        self.assertFalse(self.client.get(url).json()['unlocked'])
        self.assertEqual(self.client.post(url + 'test/', {'answer': 1}, format='json').json(), {'unlocked': True})
        self.assertEqual(self.client.get(url).json()['name'], sign.name)
