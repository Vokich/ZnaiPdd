from rest_framework.exceptions import PermissionDenied

from app.models import Profile


ADMIN = 'admin'


def account_role(user):
    if not user.is_authenticated:
        return None
    if user.is_staff and user.is_superuser:
        return ADMIN
    profile = getattr(user, 'profile', None)
    return (profile.role or None) if profile else None


def is_child(user):
    return account_role(user) == Profile.Role.CHILD


def can_submit_lesson_reports(user):
    return account_role(user) == Profile.Role.TEACHER


def require_report_access(user):
    if not can_submit_lesson_reports(user):
        raise PermissionDenied('Право на отчёты выдаёт администратор после проверки учётной записи.')
