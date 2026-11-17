from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from rest_framework.test import APIClient

from .forms import JuniorPddTestForm
from .models import Certificate, Municipality, Organization, Profile, RoadSign, TeacherLessonReport, TestResult, UserSignProgress


class SessionApiTests(TestCase):
    registration = {
        'username': 'student',
        'password': 'test-password',
        'email': 'student@example.com',
        'surname1': 'Иванов',
        'name': 'Иван',
        'role': 'teacher',
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
        response = client.post('/api/users/', {**self.registration, 'password': '1'}, format='json', **csrf())
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.json())
        response = client.post('/api/users/', self.registration, format='json', **csrf())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['role'], Profile.Role.CHILD)
        self.assertEqual(client.get('/api/profile/').json()['profile']['surname1'], self.registration['surname1'])
        self.assertEqual(client.delete('/api/session/', **csrf()).status_code, 204)
        self.assertEqual(client.get('/api/profile/').status_code, 403)

        credentials = {key: self.registration[key] for key in ('username', 'password')}
        response = client.post('/api/session/', credentials, format='json', **csrf())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['username'], 'student')
        self.assertEqual(client.get('/api/session/').json()['user']['username'], 'student')

    def test_profile_preserves_a_legacy_municipality_on_partial_update(self):
        user = User.objects.create_user(username='legacy', email='legacy@example.com')
        Profile.objects.create(user=user, role=Profile.Role.CHILD, surname1='Иванов', name='Иван', region='Старое название')
        client = APIClient()
        client.force_login(user)
        response = client.patch('/api/profile/', {'name': 'Новое имя', 'role': 'teacher'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['profile']['name'], 'Новое имя')
        self.assertEqual(response.json()['profile']['region'], 'Старое название')
        self.assertEqual(response.json()['profile']['role'], Profile.Role.CHILD)

    def test_account_without_profile_can_complete_setup_without_report_permissions(self):
        user = User.objects.create_user(username='incomplete')
        self.assertFalse(Profile.objects.filter(user=user).exists())
        client = APIClient()
        client.force_login(user)
        self.assertIsNone(client.get('/api/profile/').json()['profile']['role'])
        response = client.patch('/api/profile/', {'name': 'Иван', 'surname1': 'Иванов', 'role': 'teacher'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['profile']['role'], Profile.Role.CHILD)
        self.assertFalse(response.json()['profile']['can_submit_reports'])
        self.assertEqual(client.get('/api/lesson-reports/').status_code, 403)


class LearningApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username='student')
        Profile.objects.create(user=self.student, role=Profile.Role.CHILD, name='Иван', surname1='Иванов')

    def create_teacher(self, username):
        user = User.objects.create_user(username=username)
        Profile.objects.create(user=user, role=Profile.Role.TEACHER, name='Анна', surname1='Петрова')
        return user

    def test_long_names_fit_both_award_templates(self):
        profile = self.student.profile
        profile.surname1, profile.name = 'Ш' * 50, 'Ж' * 50
        profile.save()
        self.client.force_login(self.student)
        for score in (18, 30):
            with self.subTest(score=score):
                result = TestResult.objects.create(
                    user=self.student, test_type='junior', score=score, total_questions=30,
                    passing_score=18, passed=True,
                )
                download = self.client.get(f'/api/tests/junior/certificate/?id={result.pk}')
                page = PdfReader(BytesIO(b''.join(download.streaming_content))).pages[0]
                width = float(page.mediabox.width)
                lines = {}

                def check_line(text, cm, tm, font, size):
                    line = text.strip()
                    if line in (profile.surname1, profile.name):
                        lines[line] = tm[5]
                        self.assertGreater(tm[4], width * .27)
                        self.assertLess(tm[4] + stringWidth(line, 'LilitaOne', size), width * .75)

                page.extract_text(visitor_text=check_line)
                self.assertEqual(set(lines), {profile.surname1, profile.name})
                self.assertGreater(lines[profile.surname1], lines[profile.name])

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
        Profile.objects.create(user=other, role=Profile.Role.CHILD, name='Анна', surname1='Петрова')
        self.client.force_login(other)
        self.assertEqual(self.client.get(f'{url}?id={result_id}').status_code, 404)
        self.assertEqual(self.client.get(f'/api/tests/junior/certificate/?id={result_id}').status_code, 404)
        self.assertEqual(TestResult.objects.count(), 1)

    def test_roles_and_report_ownership(self):
        url = '/api/lesson-reports/'
        report = {'lesson_date': '2025-09-01', 'location': 'Школа', 'participants_count': 2}
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, report, format='json').status_code, 403)
        teacher = self.create_teacher('approved')
        self.client.force_login(teacher)
        self.assertEqual(self.client.get('/api/tests/teen/').status_code, 403)
        self.assertEqual(self.client.get('/api/training-material/').status_code, 200)
        self.assertEqual(self.client.post(url, {**report, 'participants_count': 0}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {**report, 'photo_link': 'https://example.com'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {**report, 'children_list': 'Список'}, format='json').status_code, 400)
        response = self.client.post(url, report, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.client.get(url).json()), 1)
        report_id = response.json()['id']
        detail = f'{url}{report_id}/'
        self.assertEqual(self.client.get(detail).json()['participants_count'], 2)
        response = self.client.patch(detail, {'participants_count': 3, 'user': self.student.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['participants_count'], 3)
        self.assertEqual(TeacherLessonReport.objects.get(pk=report_id).user_id, teacher.pk)
        self.client.force_login(self.create_teacher('another-teacher'))
        self.assertEqual(self.client.get(url).json(), [])
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.patch(detail, {'participants_count': 4}, format='json').status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(detail).status_code, 403)

    def test_reports_and_profiles_link_to_same_optional_organization(self):
        teacher = self.create_teacher('approved')
        municipality = Municipality.objects.get(name='город Елец, Липецкая область')
        organization = Organization.objects.create(name='Школа № 1', municipality=municipality)
        self.client.force_login(teacher)
        self.assertEqual(self.client.get('/api/organizations/?q=Школа').json()[0]['id'], organization.pk)
        profile = self.client.patch('/api/profile/', {'organization': organization.pk}, format='json')
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()['profile']['organization']['id'], organization.pk)
        report = self.client.post('/api/lesson-reports/', {
            'lesson_date': '2025-09-01', 'participants_count': 2, 'organization': organization.pk,
        }, format='json')
        self.assertEqual(report.status_code, 201)
        self.assertEqual(report.json()['organization']['id'], organization.pk)
        self.assertEqual(self.client.patch(f"/api/lesson-reports/{report.json()['id']}/", {'organization': None}, format='json').status_code, 400)

    def test_route_report_validates_completion_on_create_and_partial_update(self):
        url = '/api/lesson-reports/'
        report = {'lesson_date': '2026-11-16', 'location': 'Учебный класс', 'participants_count': 5}
        self.client.force_login(self.create_teacher('route-teacher'))
        options = self.client.get(url + 'options/').json()
        self.assertEqual({option['id'] for option in options}, {'pedestrian', 'detour', 'cycling'})
        for additions in (
            {'completed_count': 0},
            {'route_level': 'detour'},
            {'route_level': 'detour', 'completed_count': -1},
            {'route_level': 'detour', 'completed_count': 6},
            {'route_level': 'unknown', 'completed_count': 2},
        ):
            with self.subTest(additions=additions):
                self.assertEqual(self.client.post(url, {**report, **additions}, format='json').status_code, 400)
        response = self.client.post(url, {**report, 'route_level': 'detour', 'completed_count': 0}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['completed_count'], 0)
        detail = f"{url}{response.json()['id']}/"
        response = self.client.patch(detail, {'completed_count': 5}, format='json')
        self.assertEqual(response.json()['completed_count'], 5)
        self.assertEqual(self.client.patch(detail, {'participants_count': 4}, format='json').status_code, 400)
        response = self.client.patch(detail, {'route_level': ''}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['completed_count'])

    def test_report_admin_and_legacy_form_reject_private_fields(self):
        teacher = self.create_teacher('approved')
        data = {'lesson_date': '2025-09-01', 'location': 'Школа', 'participants_count': 2, 'children_list': 'Имена'}
        self.client.force_login(teacher)
        legacy = self.client.post(reverse('pdd-teacher'), data)
        self.assertTrue(legacy.context['form'].non_field_errors())

        admin = User.objects.create_superuser(username='admin', password='test-admin-password')
        self.client.force_login(admin)
        admin_url = reverse('admin:app_teacherlessonreport_add')
        response = self.client.get(admin_url)
        self.assertNotContains(response, 'name="children_list"')
        self.assertNotContains(response, 'name="photo_link"')
        response = self.client.post(admin_url, {**data, 'user': teacher.pk, '_save': True})
        self.assertTrue(response.context['adminform'].form.non_field_errors())
        self.assertFalse(TeacherLessonReport.objects.exists())

    def test_published_sign_is_public_but_collection_requires_a_correct_answer(self):
        sign = RoadSign.objects.create(
            slug='crosswalk', number='5.19.1', name='Пешеходный переход',
            category=RoadSign.Category.SPECIAL_MANDATORY, is_published=True,
            short_description='Переход', source_url='https://example.org/rules/',
            question='Что здесь?', answer_options=['Переход', 'Остановка'], correct_answer=1,
        )
        url = f'/api/signs/{sign.slug}/'
        guest = self.client.get(url).json()
        self.assertEqual(guest['name'], sign.name)
        self.assertIn('/road-signs/5.19.1.png', guest['image'])
        self.assertEqual(guest['source_url'], sign.source_url)
        self.assertFalse(guest['unlocked'])
        self.assertNotIn('question', guest)
        self.assertEqual(self.client.get(url + 'test/').status_code, 403)
        for query in ('№ 5.19', 'ПЕШЕХОДНЫЙ'):
            response = self.client.get('/api/signs/', {'q': query, 'category': sign.category})
            self.assertEqual([item['slug'] for item in response.json()['signs']], [sign.slug])
        self.assertContains(self.client.get(reverse('sign_detail', args=[sign.slug])), sign.name)
        self.assertFalse(UserSignProgress.objects.exists())

        self.client.force_login(self.student)
        quiz = self.client.get(url + 'test/').json()
        self.assertEqual({option['id'] for option in quiz['options']}, {1, 2})
        self.assertNotIn('correct_answer', quiz)
        self.assertEqual(self.client.post(url + 'test/', {'answer': 2}, format='json').status_code, 400)
        self.assertFalse(self.client.get(url).json()['unlocked'])
        self.assertEqual(self.client.post(url + 'test/', {'answer': 1}, format='json').json(), {'unlocked': True})
        first_visit = UserSignProgress.objects.get(user=self.student, sign=sign).test_passed_at
        self.client.post(url + 'test/', {'answer': 1}, format='json')
        self.assertEqual(UserSignProgress.objects.get(user=self.student, sign=sign).test_passed_at, first_visit)
        self.assertTrue(self.client.get(url).json()['unlocked'])
        self.assertEqual(self.client.get('/api/signs/').json()['unlocked_count'], 1)

    def test_unpublished_sign_hides_card_quiz_and_uploaded_image_without_losing_progress(self):
        sign = RoadSign.objects.create(
            slug='draft', name='Черновик', image='signs/pilot.png', category=RoadSign.Category.INFO,
            short_description='Учебный пример', is_published=False,
            question='Вопрос', answer_options=['Да', 'Нет'],
        )
        progress = UserSignProgress.objects.create(user=self.student, sign=sign, unlocked=True)
        self.client.force_login(self.student)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            image = Path(media_root) / 'signs/pilot.png'
            image.parent.mkdir()
            image.write_bytes(b'image fixture')
            self.assertEqual(self.client.get('/api/signs/').json()['total'], 0)
            self.assertEqual(self.client.get('/api/signs/draft/').status_code, 404)
            self.assertEqual(self.client.get('/api/signs/draft/test/').status_code, 404)
            self.assertEqual(self.client.get('/media/signs/pilot.png').status_code, 404)
            sign.is_published = True
            sign.save(update_fields=['is_published'])
            response = self.client.get('/media/signs/pilot.png')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertEqual(b''.join(response.streaming_content), b'image fixture')
            self.assertTrue(self.client.get('/api/signs/draft/').json()['unlocked'])
            self.assertTrue(UserSignProgress.objects.filter(pk=progress.pk, unlocked=True).exists())

    def test_starter_signs_can_be_loaded_again_without_republishing_edited_cards(self):
        call_command('seed_road_signs', stdout=StringIO())
        count = RoadSign.objects.count()
        crosswalk = RoadSign.objects.get(number='5.19.1', is_published=True)
        crosswalk.is_published = False
        crosswalk.save(update_fields=['is_published'])
        call_command('seed_road_signs', stdout=StringIO())
        self.assertEqual(RoadSign.objects.count(), count)
        crosswalk.refresh_from_db()
        self.assertFalse(crosswalk.is_published)
