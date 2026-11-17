from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import Profile


class MunicipalitySearchTests(SimpleTestCase):
    def search(self, query):
        response = self.client.get(reverse('municipality_search'), {'q': query})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_search_by_region_returns_only_its_municipalities(self):
        data = self.search('Липецкая область')
        self.assertFalse(data['more'])
        self.assertIn('город Елец, Липецкая область', data['results'])
        self.assertIn('город Липецк, Липецкая область', data['results'])
        self.assertTrue(all(value.endswith(', Липецкая область') for value in data['results']))
        self.assertEqual(self.search('  ЛИПЕЦКАЯ  обл.  '), data)

    def test_full_region_name_does_not_limit_results(self):
        data = self.search('Республика Башкортостан')
        self.assertFalse(data['more'])
        self.assertGreater(len(data['results']), 50)

    def test_search_by_municipality_and_region(self):
        data = self.search('елец липецкая область')
        self.assertIn('город Елец, Липецкая область', data['results'])
        self.assertNotIn('город Липецк, Липецкая область', data['results'])
        self.assertEqual(self.search('несуществующиймуниципалитет')['results'], [])


class LegacyProfilePageTests(TestCase):
    form_data = {
        'username': 'municipality-test',
        'password': 'test-password',
        'email': 'municipality@example.com',
        'surname1': 'Иванов',
        'name': 'Иван',
        'role': 'child',
    }

    def test_registration_requires_consent_and_full_name(self):
        url = reverse('reg')
        response = self.client.post(url, self.form_data)
        self.assertIn('consent', response.context['form'].errors)
        response = self.client.post(url, {**self.form_data, 'name': '', 'consent': 'on'})
        self.assertIn('name', response.context['form'].errors)
        self.assertFalse(User.objects.filter(username=self.form_data['username']).exists())

        response = self.client.post(url, {**self.form_data, 'consent': 'on', 'surname2': 'Иванович'})
        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)
        profile = User.objects.get(username=self.form_data['username']).profile
        self.assertEqual(profile.surname2, 'Иванович')
        self.assertIsNone(profile.birth_date)

    def test_profile_preserves_old_municipality_when_editing(self):
        user = User.objects.create_user(username=self.form_data['username'], email=self.form_data['email'])
        profile = Profile.objects.create(user=user, role=Profile.Role.CHILD, region='Старое название')
        self.client.force_login(user)

        url = reverse('profile_edit')
        response = self.client.post(url, {**self.form_data, 'region': 'Новый муниципалитет'})
        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
        profile.refresh_from_db()
        self.assertEqual(profile.region, 'Старое название')
