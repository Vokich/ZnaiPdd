from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from .models import NewsPost, PracticeExercise, PracticeResult, PracticeVersion, Profile, RoadSign
from .practice import publish_practice, withdraw_practice


def upload_png(name, mode='RGB'):
    buffer = BytesIO()
    color = '#dbe7fa' if mode == 'RGB' else (219, 231, 250, 0)
    Image.new(mode, (40, 30), color).save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


class PracticeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_practice', stdout=StringIO())
        cls.student = User.objects.create_user(username='practice-student')
        Profile.objects.create(user=cls.student, role='child', name='Анна', surname1='Тестова', competition_enabled=True)
        cls.teacher = User.objects.create_user(username='practice-teacher')
        Profile.objects.create(user=cls.teacher, role='teacher')
        cls.admin = User.objects.create_superuser(username='practice-admin')

    def test_catalog_both_formats_and_sign_links(self):
        data = self.client.get('/api/practice/').json()
        self.assertEqual(len(data['items']), 10)
        self.assertEqual(sum(item['kind'] == 'Порядок действий' for item in data['items']), 5)
        filtered = self.client.get('/api/practice/?topic=cycling&difficulty=basic').json()['items']
        self.assertEqual([item['slug'] for item in filtered], ['walk-the-bike'])
        sign = self.client.get('/api/signs/pdd-8-5-1/').json()
        self.assertIn('stop-calendar', {item['slug'] for item in sign['exercises']})
        exercise = self.client.get('/api/practice/stop-calendar/').json()
        self.assertEqual([plate['number'] for plate in exercise['plates']], ['8.5.1', '8.5.2'])
        self.assertNotIn('right_meanings', exercise)
        self.assertNotIn('explanation', exercise)

    def test_guest_can_retry_and_accept_alternative_order(self):
        url = '/api/practice/zebra-check/'
        anonymous = APIClient()
        version = anonymous.get(url).json()['version']
        invalid = anonymous.post(url, {'version': version, 'answer': [1, 1, 3, 4]}, format='json')
        self.assertEqual(invalid.status_code, 400)
        wrong = anonymous.post(url, {'version': version, 'answer': [4, 1, 3, 2]}, format='json').json()
        self.assertFalse(wrong['correct'])
        self.assertIn('расстояние', wrong['explanation'])
        result = anonymous.post(url, {'version': version, 'answer': [1, 3, 2, 4]}, format='json').json()
        self.assertTrue(result['correct'])
        self.assertTrue(anonymous.get(url).json()['completed'])
        self.assertFalse(PracticeResult.objects.exists())

    def test_open_version_remains_usable_and_withdrawal_stops_it(self):
        url = '/api/practice/zebra-check/'
        old = PracticeExercise.objects.get(slug='zebra-check').published_version
        updated = PracticeVersion.objects.create(
            exercise=old.exercise, kind=old.kind, prompt='Новая карточка', explanation=old.explanation,
            source_url=old.source_url, sign=old.sign, content=old.content,
        )
        student = APIClient()
        student.force_login(self.student)
        self.assertEqual(student.get(url + f'?preview={updated.pk}').status_code, 404)
        publish_practice(updated.pk)
        self.assertEqual(student.get(url).json()['version'], updated.pk)
        for version in [old, old, updated]:
            response = student.post(url, {'version': version.pk, 'answer': [1, 2, 3, 4]}, format='json')
            self.assertTrue(response.json()['correct'])
        self.assertEqual(PracticeResult.objects.filter(user=self.student).count(), 2)
        board = student.get('/api/rating/?section=practice').json()
        self.assertEqual(board['entries'][0]['points'], 10)
        self.assertEqual(student.get('/api/rating/').json()['maximum'], 300)
        self.assertEqual(len(student.get('/api/practice/history/').json()), 2)
        self.assertEqual(APIClient().get('/api/practice/history/').status_code, 403)
        withdraw_practice(old.pk)
        self.assertEqual(student.post(url, {'version': old.pk, 'answer': [1, 2, 3, 4]}, format='json').status_code, 404)
        withdraw_practice(updated.pk)
        self.assertEqual(student.get(url).status_code, 404)
        self.assertEqual(len(student.get('/api/practice/history/').json()), 2)

    def test_admin_enters_cards_without_json_and_publishes_a_draft(self):
        self.client.force_login(self.admin)
        catalog = reverse('admin:app_practiceexercise_add')
        response = self.client.post(catalog, {
            'title': 'Новое упражнение', 'slug': 'new-exercise', 'topic': 'cycling', 'difficulty': 'basic', '_save': '1',
        })
        self.assertEqual(response.status_code, 302)
        exercise = PracticeExercise.objects.get(slug='new-exercise')
        add = reverse('admin:app_practiceversion_add')
        response = self.client.post(add, {
            'exercise': exercise.pk, 'kind': 'order', 'prompt': 'Условие', 'explanation': 'Объяснение',
            'source_url': 'https://example.org/rules/', 'cards': 'Первая\nВторая\nТретья', 'orders': '1,2,3',
            'images-TOTAL_FORMS': '0', 'images-INITIAL_FORMS': '0',
            '_save': '1',
        })
        self.assertEqual(response.status_code, 302)
        version = exercise.versions.get()
        public_url = '/api/practice/new-exercise/'
        self.assertEqual(APIClient().get(public_url).status_code, 404)
        self.assertTrue(self.client.get(public_url + f'?preview={version.pk}').json()['preview'])
        versions = reverse('admin:app_practiceversion_changelist')
        self.client.post(versions, {'action': 'publish', '_selected_action': version.pk, 'index': '0'})
        self.assertEqual(APIClient().get(public_url).status_code, 200)
        self.assertEqual(self.client.post(reverse('admin:app_practiceversion_change', args=[version.pk]),
                                          {'prompt': 'Изменено'}).status_code, 403)

    def test_plate_answer_and_lesson_report_integration(self):
        student = APIClient()
        student.force_login(self.student)
        url = '/api/practice/stop-calendar/'
        version = student.get(url).json()['version']
        self.assertFalse(student.post(url, {'version': version, 'answer': [1, 2, 1]}, format='json').json()['correct'])
        self.assertTrue(student.post(url, {'version': version, 'answer': [1, 1, 2]}, format='json').json()['correct'])

        teacher = APIClient()
        teacher.force_login(self.teacher)
        self.assertEqual(teacher.get('/api/practice/history/').json(), [])
        options = teacher.get('/api/lesson-reports/options/?include=practice').json()
        practice = next(item for item in options['practice'] if item['slug'] == 'stop-calendar')
        report = {'lesson_date': '2026-11-16', 'location': 'Класс', 'participants_count': 5,
                  'practice': practice['id'], 'completed_count': 4}
        self.assertEqual(teacher.post('/api/lesson-reports/', {**report, 'route_level': 'cycling'},
                                      format='json').status_code, 400)
        saved = teacher.post('/api/lesson-reports/', report, format='json')
        self.assertEqual(saved.status_code, 201)
        self.assertEqual(saved.json()['practice'], practice)

    def test_practice_images_follow_published_versions_and_copy_to_drafts(self):
        self.client.force_login(self.admin)
        exercise = PracticeExercise.objects.get(slug='zebra-check')
        old_version = exercise.published_version
        copy_url = reverse('admin:app_practiceversion_make_draft', args=[old_version.pk])
        self.assertContains(self.client.get(reverse('admin:app_practiceversion_change', args=[old_version.pk])),
                            'Создать черновик для правки')
        copied = self.client.post(copy_url, follow=True)
        self.assertEqual(copied.status_code, 200)
        self.assertContains(copied, 'name="new_images"')
        draft = exercise.versions.exclude(pk=old_version.pk).get()
        edit = reverse('admin:app_practiceversion_change', args=[draft.pk])
        public_url = '/api/practice/zebra-check/'
        guest = APIClient()
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            saved = self.client.post(edit, {
                'kind': 'order', 'prompt': draft.prompt, 'explanation': draft.explanation,
                'source_url': draft.source_url, 'sign': draft.sign_id,
                'cards': 'Первая\nВторая\nТретья', 'orders': '1,2,3',
                'images-TOTAL_FORMS': '1', 'images-INITIAL_FORMS': '0',
                'images-0-image': upload_png('diagram.png', mode='RGBA'),
                'images-0-caption': 'Схема перехода', 'images-0-alt': 'Стрелка у перехода', 'images-0-order': '0',
                '_save': '1',
            })
            self.assertEqual(saved.status_code, 302)
            image = draft.images.get()
            url = image.image.url
            self.assertEqual(guest.get(url).status_code, 404)
            self.assertEqual(guest.get(public_url).json()['images'], [])
            preview = self.client.get(public_url + f'?preview={draft.pk}').json()
            self.assertEqual(preview['images'][0]['url'], url)
            with Image.open(Path(directory, image.image.name)) as prepared:
                self.assertEqual(prepared.mode, 'RGBA')
                self.assertEqual(prepared.getpixel((0, 0))[3], 0)

            versions = reverse('admin:app_practiceversion_changelist')
            self.client.post(versions, {'action': 'publish', '_selected_action': draft.pk, 'index': '0'})
            public_image = guest.get(public_url).json()['images'][0]
            self.assertEqual(public_image['caption'], 'Схема перехода')
            self.assertEqual(public_image['alt'], 'Стрелка у перехода')
            response = guest.get(url)
            self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))

            self.client.post(reverse('admin:app_practiceversion_make_draft', args=[draft.pk]))
            new_draft = exercise.versions.exclude(pk__in=[old_version.pk, draft.pk]).get()
            inherited = new_draft.images.get()
            self.assertEqual((inherited.caption, inherited.image.name), (image.caption, image.image.name))
            self.assertIsNone(new_draft.published_at)
            withdraw_practice(draft.pk)
            self.assertEqual(guest.get(url).status_code, 404)


class NewsTests(TestCase):
    def event(self, slug, days=1, **fields):
        defaults = {
            'kind': 'event', 'title': slug, 'summary': 'Кратко', 'body': 'Подробно',
            'published_at': timezone.now(), 'starts_at': timezone.now() + timedelta(days=days),
            'venue': 'Онлайн', 'audience': 'Педагоги', 'organizer': 'Учебный кружок',
            'registration_url': 'https://example.org/entry',
        }
        return NewsPost.objects.create(slug=slug, **{**defaults, **fields})

    def test_feed_and_home_exclude_drafts_past_and_cancelled_events_from_upcoming(self):
        self.event('past', days=-1)
        self.event('cancelled', cancelled=True)
        self.event('draft', published_at=None)
        self.event('later', days=2)
        self.event('first', registration_deadline=timezone.now() - timedelta(hours=1))
        self.assertEqual(self.client.get('/api/news/next/').json()['event']['slug'], 'first')
        self.assertEqual([post['slug'] for post in self.client.get('/api/news/?tab=upcoming').json()['items']],
                         ['first', 'later'])
        archived = self.client.get('/api/news/?tab=archive').json()['items']
        self.assertEqual({post['slug'] for post in archived}, {'past', 'cancelled'})
        self.assertEqual(self.client.get('/api/news/draft/').status_code, 404)
        self.assertEqual(self.client.get('/api/news/first/').json()['registration_url'], '')
        self.assertEqual(self.client.get('/api/news/later/').json()['registration_url'], 'https://example.org/entry')

    def test_admin_publication_and_withdrawal_controls_cover_and_related_items(self):
        administrator = User.objects.create_superuser(username='news-admin')
        self.client.force_login(administrator)
        change_list = reverse('admin:app_newspost_changelist')
        draft = self.event('draft', published_at=None, venue='')
        self.client.post(change_list, {'action': 'publish', '_selected_action': draft.pk, 'index': '0'})
        draft.refresh_from_db()
        self.assertIsNone(draft.published_at)

        draft_sign = RoadSign.objects.create(slug='hidden', name='Черновой знак', category='info', short_description='Тест')
        draft.signs.add(draft_sign)
        guest = APIClient()
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            form = self.client.post(reverse('admin:app_newspost_add'), {
                'slug': 'reviewed', 'kind': 'news', 'title': 'Новость', 'summary': 'Описание', 'body': 'Текст',
                'timezone_name': 'Europe/Moscow', 'cover_credit': 'Учебная иллюстрация',
                'images-TOTAL_FORMS': '0', 'images-INITIAL_FORMS': '0',
                'cover': upload_png('original.png'),
                'new_images': [upload_png('first.png'), upload_png('second.png')], '_save': '1',
            })
            self.assertEqual(form.status_code, 302)
            post = NewsPost.objects.get(slug='reviewed')
            post.signs.add(draft_sign)
            first, second = post.images.all()
            self.assertEqual(guest.get(first.image.url).status_code, 404)
            self.assertEqual(guest.get(second.image.url).status_code, 404)
            second.order, second.caption = 0, 'Первая в галерее'
            second.save(update_fields=['order', 'caption'])
            self.assertTrue(Path(directory, post.cover.name).is_file())
            self.assertEqual(guest.get(post.cover.url).status_code, 404)
            self.client.post(change_list, {'action': 'publish', '_selected_action': post.pk, 'index': '0'})
            response = guest.get(post.cover.url)
            self.assertEqual(response['Content-Type'], 'image/jpeg')
            self.assertTrue(b''.join(response.streaming_content).startswith(b'\xff\xd8'))
            publication = guest.get('/api/news/reviewed/').json()
            self.assertEqual(publication['signs'], [])
            self.assertEqual([item['id'] for item in publication['images']], [second.pk, first.pk])
            self.assertEqual(publication['images'][0]['caption'], second.caption)
            photo = guest.get(second.image.url)
            self.assertTrue(b''.join(photo.streaming_content).startswith(b'\xff\xd8'))
            self.client.post(change_list, {'action': 'unpublish', '_selected_action': post.pk, 'index': '0'})
            self.assertEqual(guest.get('/api/news/reviewed/').status_code, 404)
            self.assertEqual(guest.get(post.cover.url).status_code, 404)
            self.assertEqual(guest.get(second.image.url).status_code, 404)
