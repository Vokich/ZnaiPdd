import os

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create the initial Django superuser from the environment.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
        if not username and not password:
            return
        if not username or not password.strip():
            raise CommandError('Set both DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD.')

        user_model = get_user_model()
        username_field = user_model._meta.get_field(user_model.USERNAME_FIELD)
        try:
            username = username_field.clean(user_model.normalize_username(username), None)
        except ValidationError as error:
            raise CommandError('DJANGO_SUPERUSER_USERNAME is not a valid Django username.') from error

        def initial_password():
            if password == '<случайный-длинный-пароль>':
                raise CommandError('Replace the example DJANGO_SUPERUSER_PASSWORD with your own password.')
            return make_password(password)

        user, created = user_model._default_manager.get_or_create(
            **{user_model.USERNAME_FIELD: username},
            defaults={
                'password': initial_password,
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if not (user.is_active and user.is_staff and user.is_superuser):
            raise CommandError('The configured login belongs to an account without active superuser access. Choose another login.')
        if created:
            self.stdout.write(self.style.SUCCESS('Django superuser created.'))
