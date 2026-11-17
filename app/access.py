from .models import Profile


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
