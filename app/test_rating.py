from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Municipality, Organization, Profile, RouteResult, TestResult


class RatingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        municipality = Municipality.objects.create(code='12345678', name='Учебный район')
        self.organization = Organization.objects.create(name='Учебная школа', municipality=municipality)
        self.player = User.objects.create_user(username='private-login', email='test@example.org')
        Profile.objects.create(
            user=self.player, role=Profile.Role.CHILD, surname1='Петрова', name='Анна',
            surname2='Ивановна', organization=self.organization,
        )
        self.client.force_login(self.player)

    def test_opt_in_and_out_changes_visibility_of_name_and_scores(self):
        RouteResult.objects.create(attempt='A', user=self.player, level='pedestrian', score=5, total=6, mistakes=1)
        self.assertEqual(APIClient().get('/api/rating/').status_code, 403)
        private_rating = self.client.get('/api/rating/').json()
        self.assertEqual(private_rating['entries'], [])
        self.assertEqual(private_rating['my_points'], 21)
        self.assertEqual(self.client.get('/api/profile/').json()['rating'], {
            'points': 21, 'maximum': 200,
            'directions': [{'id': 'routes', 'points': 21}, {'id': 'tests', 'points': 0}],
        })
        self.assertEqual(self.client.patch('/api/competition/', {'enabled': True}, format='json').status_code, 200)
        row = self.client.get('/api/rating/').json()['entries'][0]
        self.assertEqual(row, {
            'place': 1, 'name': 'Петрова Анна Ивановна', 'organization': 'Учебная школа',
            'points': 21, 'is_current_user': True,
        })
        self.client.patch('/api/competition/', {'enabled': False}, format='json')
        self.assertEqual(self.client.get('/api/rating/').json()['entries'], [])
        self.assertTrue(RouteResult.objects.filter(user=self.player).exists())

    def test_rating_filters_and_balances_best_results_across_directions(self):
        Profile.objects.filter(user=self.player).update(competition_enabled=True)
        for attempt, level, score, total in [
            ('A', 'pedestrian', 6, 6), ('B', 'pedestrian', 4, 6),
            ('C', 'detour', 8, 8), ('D', 'cycling', 9, 9),
        ]:
            RouteResult.objects.create(attempt=attempt, user=self.player, level=level, score=score, total=total, mistakes=0)
        TestResult.objects.create(user=self.player, test_type='teen', score=24, total_questions=30, passing_score=18)
        TestResult.objects.create(user=self.player, test_type='junior', score=15, total_questions=20, passing_score=18)
        other = User.objects.create_user(username='unaffiliated')
        Profile.objects.create(user=other, surname1='Иванов', name='Иван', competition_enabled=True)
        TestResult.objects.create(user=other, test_type='teen', score=24, total_questions=30, passing_score=18)

        response = self.client.get('/api/rating/', {'organization': self.organization.pk, 'municipality': '12345678'}).json()
        self.assertEqual(response['maximum'], 200)
        self.assertEqual([entry['points'] for entry in response['entries']], [180])
        response = self.client.get('/api/rating/', {'section': 'route-pedestrian'}).json()
        self.assertEqual(response['maximum'], 6)
        self.assertEqual([entry['points'] for entry in response['entries']], [6])
        response = self.client.get('/api/rating/', {'section': 'test-teen'}).json()
        self.assertEqual([(entry['place'], entry['points']) for entry in response['entries']], [(1, 80), (1, 80)])
        response = self.client.get('/api/rating/', {'organization': 'none'}).json()
        self.assertEqual([entry['name'] for entry in response['entries']], ['Иванов Иван'])
