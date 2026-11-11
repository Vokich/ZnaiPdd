from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


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


class MunicipalityFormTests(TestCase):
    region = 'город Елец, Липецкая область'
    form_data = {
        'username': 'municipality-test',
        'password': 'test-password',
        'email': 'municipality@example.com',
        'surname1': 'Иванов',
        'name': 'Иван',
        'school': 'Школа',
        'birth_date': '2010-01-01',
        'role': 'child',
    }

    def test_registration_requires_a_municipality_and_saves_it(self):
        url = reverse('reg')
        response = self.client.post(url, {**self.form_data, 'region': 'Липецкая область'})
        self.assertFormError(response.context['form'], 'region', 'Выберите муниципалитет из списка')
        self.assertFalse(User.objects.filter(username=self.form_data['username']).exists())

        response = self.client.post(url, {**self.form_data, 'region': self.region})
        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)
        self.assertEqual(User.objects.get(username=self.form_data['username']).profile.region, self.region)

    def test_profile_keeps_old_value_until_a_new_municipality_is_selected(self):
        user = User.objects.create_user(username=self.form_data['username'], email=self.form_data['email'])
        profile = user.profile
        profile.role = self.form_data['role']
        profile.region = 'Старое название'
        profile.save(update_fields=['role', 'region'])
        self.client.force_login(user)

        url = reverse('profile_edit')
        self.assertContains(self.client.get(url), reverse('municipality_search'))
        response = self.client.post(url, {**self.form_data, 'region': 'Старое название'})
        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
        profile.refresh_from_db()
        self.assertEqual(profile.region, 'Старое название')

        response = self.client.post(url, {**self.form_data, 'region': self.region})
        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
        profile.refresh_from_db()
        self.assertEqual(profile.region, self.region)
