from io import StringIO
from unittest.mock import patch

from django.contrib.auth import authenticate, get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase


class BootstrapAdminTests(TestCase):
    username = 'bootstrap-test-admin'
    password = 'test-admin-password-2384'

    def bootstrap(self, username, password):
        with patch.dict('os.environ', {
            'DJANGO_SUPERUSER_USERNAME': username,
            'DJANGO_SUPERUSER_PASSWORD': password,
        }):
            call_command('bootstrap_admin', stdout=StringIO())

    def test_creates_active_superuser_and_preserves_password_on_restart(self):
        self.bootstrap(self.username, self.password)
        self.bootstrap(self.username, 'another-test-password')

        user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active and user.is_staff and user.is_superuser)
        self.assertEqual(get_user_model().objects.filter(username=self.username).count(), 1)

    def test_does_not_grant_permissions_to_an_existing_user(self):
        user = get_user_model().objects.create_user(username=self.username, password='original-password')

        with self.assertRaisesMessage(CommandError, 'Choose another login'):
            self.bootstrap(self.username, self.password)

        user.refresh_from_db()
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertTrue(user.check_password('original-password'))

    def test_requires_both_values_when_configured(self):
        self.bootstrap('', '')
        with self.assertRaisesMessage(CommandError, 'Set both'):
            self.bootstrap(self.username, '')
        self.assertFalse(get_user_model().objects.exists())
