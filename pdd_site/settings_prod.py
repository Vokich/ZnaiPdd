import os

from .settings import *
from django.core.exceptions import ImproperlyConfigured


DEBUG = False
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set DJANGO_SECRET_KEY for the prod profile.')
if not os.environ.get('POSTGRES_HOST') or not POSTGRES_DATABASE['PASSWORD']:
    raise ImproperlyConfigured('Set POSTGRES_HOST and POSTGRES_PASSWORD for the prod profile.')
ALLOWED_HOSTS = [os.environ.get('DJANGO_DOMAIN', 'xn--80aiajlwq.xn--p1ai')]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 86400
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
