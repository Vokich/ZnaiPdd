from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest import skipUnless

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import ClassroomAttempt, ClassroomQuiz, ClassroomRun, PracticeResult, Profile, RouteProgress, TeacherLessonReport


ROOT = '/api/classroom/'


def teacher(name):
    user = User.objects.create_user(username=name)
    Profile.objects.create(user=user, role=Profile.Role.TEACHER)
    client = APIClient()
    client.force_login(user)
    return client


def post(client, path, **data):
    return client.post(path, data, format='json')


class ClassroomTests(TestCase):
    def setUp(self):
        self.owner = teacher('teacher')
        self.other = teacher('other')
        self.guest = APIClient()
        self.quiz = ClassroomQuiz.objects.filter(owner=None).first()

    def start(self, **data):
        run = post(self.owner, ROOT, **data).json()
        return ROOT + 'runs/' + run['id'] + '/', run

    def test_both_lessons_use_group_reports_and_no_personal_progress(self):
        for lesson in self.owner.get(ROOT).json()['lessons']:
            path, run = self.start(lesson=lesson['id'])
            steps = self.owner.get(path).json()['steps']
            self.assertEqual(len(steps), 3)
            self.assertNotIn('explanation', str(steps))
            self.assertTrue(post(self.owner, path, step=1, answer=[1, 2, 3, 4]).json()['correct'])
            self.assertFalse(post(self.owner, path, step=1, answer=[4, 3, 2, 1]).json()['correct'])
            self.assertTrue(post(self.owner, path, step=2, answer=steps[2]['choices'][-1]['id']).json()['correct'])
            self.assertEqual(self.other.get(path).status_code, 404)
            report = dict(classroom=run['id'], lesson_date='2026-11-18', location='Кабинет', participants_count=24)
            self.assertEqual(post(self.owner, '/api/lesson-reports/', **report, completed_count=1).status_code, 400)
            saved = post(self.owner, '/api/lesson-reports/', **report).json()
            self.assertEqual(saved['participants_count'], 24)
            self.assertEqual(post(self.owner, '/api/lesson-reports/', **report).json()['id'], saved['id'])
        self.assertEqual(TeacherLessonReport.objects.count(), 2)
        self.assertFalse(RouteProgress.objects.exists())
        self.assertFalse(PracticeResult.objects.exists())

    def test_join_save_retry_close_and_retention(self):
        path, run = self.start(quiz=self.quiz.pk)
        join = ROOT + 'join/' + run['code'] + '/'
        self.assertEqual(self.owner.get(path + 'qr/')['Content-Type'], 'image/svg+xml')
        self.assertFalse(self.guest.get(join).json()['joined'])
        self.assertTrue(post(self.guest, join, action='join').json()['joined'])
        self.assertEqual(post(self.guest, join, action='begin').status_code, 400)
        post(self.owner, path, action='start')
        post(self.owner, path, action='lock')
        self.assertEqual(post(APIClient(), join, action='join').status_code, 400)
        attempt = post(self.guest, join, action='begin').json()
        self.assertNotIn('correct', str(attempt))
        self.assertNotIn('explanation', str(attempt))
        answers = [0] * len(attempt['questions'])
        body = dict(revision=0, answers=answers)
        self.assertEqual(post(self.guest, join, action='save', **body).status_code, 200)
        self.assertEqual(post(self.guest, join, action='save', **body).status_code, 409)
        resumed = post(self.guest, join, action='join').json()
        self.assertEqual(resumed['answers'], answers)
        body['revision'] = resumed['revision']
        accepted = post(self.guest, join, action='submit', **body).json()
        self.assertTrue(accepted['submitted'])
        self.assertNotIn('score', accepted)
        self.assertEqual(post(self.guest, join, action='save', **body).status_code, 400)
        final = post(self.owner, path, action='close').json()
        self.assertEqual(final['counts'], dict(connected=1, started=1, submitted=1))
        result = post(self.guest, join, action='submit', **body).json()
        self.assertIn('correct', result['questions'][0])
        self.assertEqual(result['score'], final['summary']['average'])
        self.assertEqual(self.other.get(path).status_code, 404)
        self.assertNotIn('score', APIClient().get(join).json())
        report = post(self.owner, '/api/lesson-reports/', classroom=run['id'], lesson_date='2026-11-18',
                      location='Школа', participants_count=2, completed_count=0).json()
        self.assertEqual(report['classroom']['submitted'], 1)
        self.assertEqual(report['completed_count'], 0)
        ClassroomRun.objects.update(review_until=timezone.now() - timedelta(seconds=1))
        call_command('cleanup_classroom')
        self.assertFalse(ClassroomAttempt.objects.exists())
        self.assertEqual(self.owner.get(path).json()['summary'], final['summary'])
        self.assertNotIn('answers', self.guest.get(join).json())

    def test_versions_archive_ownership_and_draft_validation(self):
        tests = ROOT + 'tests/'
        draft = post(self.owner, tests, title='Класс').json()
        path = tests + str(draft['id']) + '/'
        self.assertEqual(self.guest.get(tests).status_code, 403)
        self.assertEqual(self.other.get(path).status_code, 404)
        self.assertEqual(post(self.owner, path, action='publish', revision=1).status_code, 400)
        q = dict(text='Вопрос', options=['А', 'Б'], correct=0)
        ready = post(self.owner, path, action='publish', revision=1, title='Первый тест', questions=[q]).json()
        first_path, first = self.start(quiz=draft['id'])
        self.assertEqual(first['version'], 1)
        saved = post(self.owner, path, action='save', revision=ready['revision'], title='Новый черновик', questions=[]).json()
        self.assertFalse(saved['ready'])
        self.assertEqual(self.start(quiz=draft['id'])[1]['title'], 'Первый тест')
        q['correct'] = 1
        changed = post(self.owner, path, action='publish', revision=saved['revision'], title='Второй тест', questions=[q]).json()
        _, second = self.start(quiz=draft['id'])
        self.assertEqual(second['version'], 2)
        self.assertNotEqual(first['code'], second['code'])
        self.assertEqual(self.owner.get(first_path).json()['title'], 'Первый тест')
        self.assertEqual(ClassroomRun.objects.get(pk=first['id']).version.questions[0]['correct'], 0)
        self.assertEqual(post(self.other, ROOT, quiz=draft['id']).status_code, 404)
        archived = post(self.owner, path, action='archive', revision=changed['revision']).json()
        self.assertTrue(archived['archived'])
        self.assertEqual(post(self.owner, ROOT, quiz=draft['id']).status_code, 404)
        self.assertEqual(self.owner.get(first_path).status_code, 200)
        copy = post(self.owner, path, action='copy').json()
        self.assertFalse(copy['archived'])
        self.assertEqual(self.owner.delete(tests + str(copy['id']) + '/', {'revision': 1}, format='json').status_code, 204)

    def test_server_deadlines_apply_without_teacher_tab(self):
        for started in (False, True):
            path, run = self.start(quiz=self.quiz.pk)
            join = ROOT + 'join/' + run['code'] + '/'
            post(self.guest, join, action='join')
            if started:
                post(self.owner, path, action='start')
                post(self.guest, join, action='begin')
            ClassroomRun.objects.filter(pk=run['id']).update(deadline=timezone.now() - timedelta(seconds=1))
            self.assertEqual(post(APIClient(), join, action='join').status_code, 400)
            self.assertEqual(post(self.guest, join, action='submit', revision=0, answers=[0, 0, 0]).status_code, 400)
            self.assertEqual(self.owner.get(path).json()['summary']['submitted'], 0)
            self.assertEqual(self.guest.get(join).json()['state'], 'closed')

    def test_codes_limit_failed_lookups_and_student_cannot_manage(self):
        cache.clear()
        child = User.objects.create_user(username='child')
        Profile.objects.create(user=child, role=Profile.Role.CHILD)
        self.guest.force_login(child)
        self.assertEqual(post(self.guest, ROOT, quiz=self.quiz.pk).status_code, 403)
        for _ in range(18):
            self.assertEqual(self.guest.get(ROOT + 'join/invalid/').status_code, 404)
        self.assertEqual(self.guest.get(ROOT + 'join/invalid/').status_code, 429)
        cache.clear()


@skipUnless(connection.vendor == 'postgresql', 'Проверка конкурентных записей на PostgreSQL')
class ClassroomConcurrencyTests(TransactionTestCase):
    def test_class_of_thirty_and_duplicate_submissions(self):
        owner = teacher('load-teacher')
        quiz = ClassroomQuiz.objects.filter(owner=None).first()
        run = post(owner, ROOT, quiz=quiz.pk).json()
        path = ROOT + 'runs/' + run['id'] + '/'
        join = ROOT + 'join/' + run['code'] + '/'
        post(owner, path, action='start')
        pupils = [APIClient() for _ in range(30)]

        def connect(client):
            try:
                self.assertEqual(post(client, join, action='join').status_code, 200)
                self.assertEqual(post(client, join, action='begin').status_code, 200)
            finally:
                close_old_connections()

        def submit(client):
            try:
                response = post(client, join, action='submit', answers=[0, 0, 0], revision=0)
                self.assertTrue(response.json()['submitted'])
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=30) as pool:
            list(pool.map(connect, pupils))
            list(pool.map(submit, [client for pupil in pupils for client in (pupil, pupil)]))
        final = post(owner, path, action='close').json()
        self.assertEqual(final['counts'], {'connected': 30, 'started': 30, 'submitted': 30})
