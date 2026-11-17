from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .models import Profile, RouteResult


class AdminJumpTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="admin-jump-test", is_staff=True)
        self.client.force_login(self.staff)

    def allow(self, codename):
        self.staff.user_permissions.add(
            Permission.objects.get(content_type__app_label="app", codename=codename)
        )

    def palette(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, 'id="admin-jump"')
        return response.content.decode().partition('id="admin-jump"')[2].partition("</dialog>")[0]

    def test_view_permission_does_not_expose_creation_or_other_sections(self):
        self.allow("view_roadsign")

        palette = self.palette()

        self.assertIn(reverse("admin:app_roadsign_changelist"), palette)
        self.assertNotIn(reverse("admin:app_roadsign_add"), palette)
        self.assertNotIn("/admin/auth/group/", palette)

    def test_add_permission_exposes_the_creation_action(self):
        self.allow("add_roadsign")

        self.assertIn(reverse("admin:app_roadsign_add"), self.palette())

    def test_account_form_assigns_access_with_one_profile_field(self):
        User = get_user_model()
        admin = User.objects.create_superuser(username='administrator', password='test-admin-password')
        user = User.objects.create_user(username='portal-user')
        self.client.force_login(admin)
        url = reverse('admin:auth_user_change', args=[user.pk])
        response = self.client.get(url)
        self.assertContains(response, 'name="account_role"')
        for field in ('groups', 'user_permissions', 'is_staff', 'is_superuser'):
            self.assertNotContains(response, f'name="{field}"')
        for role, staff in [('teacher', False), ('admin', True), ('child', False)]:
            response = self.client.post(url, {
                'username': user.username, 'account_role': role, 'is_active': 'on', '_save': '1',
            })
            self.assertEqual(response.status_code, 302)
            user.refresh_from_db()
            self.assertEqual(user.is_staff, staff)
            self.assertEqual(user.is_superuser, staff)
            self.assertEqual(Profile.objects.get(user=user).role, 'child' if staff else role)
        self.client.force_login(user)
        self.assertEqual(self.client.post(url, {'account_role': 'admin'}).status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_route_results_allow_administrator_to_correct_score_and_mistakes(self):
        User = get_user_model()
        admin = User.objects.create_superuser(username='route-admin')
        result = RouteResult.objects.create(
            attempt='sample-route', user=self.staff, level='cycling', score=8, total=9, mistakes=1,
            rule_reviews=[{'rule': 'ПДД, пункт 24.1', 'opened_at': '2026-11-15T09:34:56+00:00'}],
        )
        index = reverse('admin:app_routeresult_changelist')
        detail = reverse('admin:app_routeresult_change', args=[result.pk])
        self.assertEqual(self.client.get(index).status_code, 403)
        self.assertEqual(self.client.post(detail, {'score': 6, 'mistakes': 3}).status_code, 403)
        self.client.force_login(admin)
        self.assertIn(index, self.palette())
        response = self.client.get(index, {'level': 'cycling', 'q': self.staff.username})
        self.assertContains(response, self.staff.username)
        self.assertContains(response, '8 из 9')
        response = self.client.get(detail)
        self.assertContains(response, 'ПДД, пункт 24.1')
        self.assertContains(response, '15.11.2026 12:34:56')
        invalid = self.client.post(detail, {'score': 10, 'mistakes': 3, '_save': '1'})
        self.assertContains(invalid, 'Баллы не могут превышать максимум за маршрут.')
        result.refresh_from_db()
        self.assertEqual((result.score, result.mistakes), (8, 1))
        corrected = self.client.post(detail, {'score': 6, 'mistakes': 3, 'total': 6, '_save': '1'})
        self.assertEqual(corrected.status_code, 302)
        result.refresh_from_db()
        self.assertEqual((result.score, result.mistakes, result.total), (6, 3, 9))
        self.assertEqual(result.rule_reviews[0]['rule'], 'ПДД, пункт 24.1')
