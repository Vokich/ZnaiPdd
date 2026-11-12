from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse


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
        self.assertNotIn(reverse("admin:auth_group_changelist"), palette)

    def test_add_permission_exposes_the_creation_action(self):
        self.allow("add_roadsign")

        self.assertIn(reverse("admin:app_roadsign_add"), self.palette())
