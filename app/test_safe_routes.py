from io import BytesIO
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from pypdf import PdfReader
from rest_framework.test import APIClient

from .models import Profile, RouteProgress, RouteResult
from .route_api import SESSION_KEY
from .route_levels import LEVELS
from .safe_routes import district


class RouteGeneratorTests(SimpleTestCase):
    def test_all_safe_branches_can_reach_school(self):
        def reaches_school(points, key, visited):
            if key == 'school':
                return True
            targets = [option['target'] for option in points[key]['choices'] if option['target']]
            return any(reaches_school(points, target, visited | {key}) for target in targets if target not in visited)

        for level in LEVELS:
            for seed in range(12):
                with self.subTest(level=level, seed=seed):
                    points, edges = district(level, seed)
                    self.assertEqual(sum(point['decision'] for point in points.values()), LEVELS[level]['total'])
                    for key, point in points.items():
                        self.assertTrue(reaches_school(points, key, set()))
                        for choice in point['choices']:
                            if choice['target']:
                                self.assertIn(frozenset((key, choice['target'])), [frozenset(edge) for edge in edges])


class RouteApiTests(TestCase):
    url = '/api/safe-route/'

    def setUp(self):
        self.client = APIClient()

    def start(self, level):
        response = self.client.post(self.url, {'action': 'start', 'level': level}, format='json')
        self.assertEqual(response.status_code, 200)
        return response.json()['route']

    def move(self, route, choice):
        response = self.client.post(self.url, {
            'action': 'move', 'id': route['id'], 'revision': route['revision'], 'choice': choice,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        return response.json()['route']

    def review(self, route):
        data = urlencode({
            'action': 'open-rule', 'id': route['id'], 'revision': route['revision'],
        })
        response = self.client.post(self.url, data, content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response['Location'].startswith('https://www.mos.ru/'))
        return self.client.get(self.url).json()['route']

    def finish(self, route, client_state):
        points, _ = district(route['level'], client_state['seed'], client_state['version'])
        for _ in range(len(points)):
            if route['completed']:
                return route
            safe = next(option for option in points[route['current']]['choices'] if option['target'])
            route = self.move(route, safe['id'])
        self.fail('Route did not reach the school.')

    def test_guest_can_correct_a_mistake_finish_and_download_own_pdf(self):
        route = self.start('cycling')
        pdf = self.url + route['id'] + '/memento/'
        self.assertEqual(self.client.get(pdf).status_code, 404)
        route = self.move(route, 'go')
        failed = self.move(route, 'traffic')
        self.assertEqual(self.move(route, 'traffic'), failed)
        self.assertEqual(failed['current'], route['current'])
        self.assertEqual(failed['score'], -1)
        self.assertFalse(failed['feedback']['accepted'])
        self.assertEqual(failed['choices'], [])
        bypass = self.client.post(self.url, {
            'action': 'move', 'id': failed['id'], 'revision': failed['revision'], 'choice': 'cycle',
        }, format='json')
        self.assertEqual(bypass.status_code, 403)
        self.assertEqual(self.client.get(self.url).json()['route'], failed)
        opened = self.review(failed)
        self.assertEqual(opened['rules_opened'], 1)
        self.assertEqual(opened['required_rule'], '')
        self.assertEqual(self.review(failed), opened)
        repeated = self.move(opened, 'traffic')
        self.assertEqual(repeated['score'], -2)
        route = self.move(self.review(repeated), 'cycle')
        self.assertEqual(route['corrected'], 2)
        finished = self.finish(route, self.client.session[SESSION_KEY])
        self.assertTrue(finished['completed'])
        self.assertEqual(finished['score'], finished['total'] - 2)
        self.assertEqual(APIClient().get(pdf).status_code, 404)
        response = self.client.get(pdf)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        pages = PdfReader(BytesIO(b''.join(response.streaming_content))).pages
        self.assertGreater(len(pages), 1)
        self.assertIn('Безопасный маршрут', pages[0].extract_text())

    def test_detour_can_return_without_scoring_the_same_decision_again(self):
        route = self.move(self.start('detour'), 'go')
        state = self.client.session[SESSION_KEY]
        points, _ = district('detour', state['seed'])
        while route['scene']['kind'] != 'works':
            safe = next(option for option in points[route['current']]['choices'] if option['target'])
            route = self.move(route, safe['id'])
        failed = self.move(route, 'fence')
        self.assertEqual(failed['score'], route['score'] - 1)
        fork = self.review(failed)
        first = self.move(fork, 'park')
        fork = self.move(first, 'back')
        second = self.move(fork, 'walkway')
        self.assertEqual(second['score'], first['score'])
        self.assertEqual(second['corrected'], 1)
        self.assertNotIn('park', second['path'])
        self.assertTrue(self.finish(self.move(second, 'go'), state)['completed'])

    def test_guest_route_can_be_attached_and_resumed_after_new_login(self):
        user = User.objects.create_user(username='route-student', password='fixture-password')
        route = self.move(self.start('pedestrian'), 'go')
        self.client.post('/api/session/', {'username': user.username, 'password': 'fixture-password'}, format='json')
        data = self.client.get(self.url).json()
        self.assertIsNone(data['route'])
        self.assertEqual(data['guest_route']['id'], route['id'])
        attached = self.client.post(self.url, {'action': 'attach', 'id': route['id']}, format='json').json()
        self.assertIsNone(attached['guest_route'])
        self.assertEqual(attached['route'], route)
        other_browser = APIClient()
        other_browser.force_login(user)
        self.assertEqual(other_browser.get(self.url).json()['route'], route)

    def test_completed_attempt_keeps_result_and_review_when_starting_another(self):
        user = User.objects.create_user(username='route-ranking')
        self.client.force_login(user)
        route = self.move(self.start('cycling'), 'go')
        route = self.review(self.move(route, 'traffic'))
        route = self.finish(route, RouteProgress.objects.get(user=user).state)
        result = RouteResult.objects.get(user=user, attempt=route['id'])
        self.assertEqual(result.score, 8)
        self.assertEqual(result.total, 9)
        self.assertEqual(result.rule_reviews[0]['rule'], 'ПДД, пункт 24.1')
        self.assertIsNotNone(result.rule_reviews[0]['opened_at'])
        self.start('cycling')
        self.assertEqual(RouteResult.objects.get(user=user).pk, result.pk)

    def test_keeps_old_completed_route_and_its_previous_score(self):
        user = User.objects.create_user(username='legacy-route')
        self.client.force_login(user)
        state = {
            'id': 'previous', 'version': 1, 'seed': 'fixture', 'level': 'pedestrian',
            'path': ['home', 'point-1', 'point-2', 'school'], 'solved': ['point-1', 'point-2'],
            'mistakes': ['point-1'], 'revision': 4, 'last_choice': 'check', 'feedback': None,
        }
        RouteProgress.objects.create(user=user, state=state)
        saved = self.client.get(self.url).json()['route']
        self.assertEqual(saved['score'], 2)
        self.assertFalse(saved['ranked_version'])
        self.assertEqual(self.client.get(self.url + 'previous/memento/').status_code, 200)
        self.assertFalse(RouteResult.objects.exists())

    def test_corrected_result_is_used_in_cabinet_pdf_and_rating(self):
        user = User.objects.create_user(username='corrected-route')
        Profile.objects.create(user=user, role='child', name='Анна', surname1='Тестова', competition_enabled=True)
        self.client.force_login(user)
        started = self.start('cycling')
        completed = self.finish(started, RouteProgress.objects.get(user=user).state)
        administrator = APIClient()
        administrator.force_login(User.objects.create_superuser(username='result-editor'))
        detail = reverse('admin:app_routeresult_change', args=[completed['id']])
        self.assertEqual(administrator.post(detail, {'score': 7, 'mistakes': 2, '_save': '1'}).status_code, 302)

        result = self.client.get(self.url).json()['route']
        self.assertEqual((result['score'], result['mistakes'], result['total']), (7, 2, 9))
        self.assertEqual(result['path'], completed['path'])
        rating = self.client.get('/api/rating/?section=route-cycling').json()
        self.assertEqual(rating['entries'][0]['points'], 7)
        response = self.client.get(self.url + completed['id'] + '/memento/')
        reader = PdfReader(BytesIO(b''.join(response.streaming_content)))
        text = ' '.join(reader.pages[0].extract_text().split())
        self.assertIn('Баллы 7 из 9', text)
        self.assertIn('Ошибок: 2', text)
