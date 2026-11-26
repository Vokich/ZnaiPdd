import json
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.crypto import salted_hmac


def client_address(request):
    if settings.SECURE_PROXY_SSL_HEADER:
        # Caddy replaces this header before proxying. The web service has no public port.
        return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '')
    return request.META.get('REMOTE_ADDR', '')


def quota(scope, identity, limit, seconds):
    window = int(time.time()) // seconds
    key = 'quota:' + salted_hmac(scope, f'{identity}:{window}').hexdigest()
    if cache.add(key, 1, timeout=seconds + 1):
        return 0
    try:
        count = cache.incr(key)
    except ValueError:  # The interval expired before the increment.
        return 0
    return seconds - int(time.time()) % seconds if count > limit else 0


def limited(wait):
    response = JsonResponse({'detail': f'Слишком много запросов. Попробуйте через {wait} с.'}, status=429)
    response['Retry-After'] = str(wait)
    response['Cache-Control'] = 'no-store'
    return response


class RequestLimits:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        ip = client_address(request)
        limits = settings.PLATFORM_LIMITS
        wait = 0
        if request.method == 'POST' and path in ('/api/session/', '/login/', '/admin/login/'):
            wait = quota('login-ip', ip, limits['login_ip'], 60)
            if not wait:
                if request.content_type == 'application/json':
                    try:
                        data = json.loads(request.body)
                    except (ValueError, RecursionError):
                        data = {}
                else:
                    data = request.POST
                login = data.get('username') if isinstance(data, dict) else None
                if isinstance(login, str) and login:
                    wait = quota('login-pair', ip + ':' + login.strip().casefold()[:150], limits['login_pair'], 60)
        elif request.method == 'POST' and path in ('/api/users/', '/reg/'):
            wait = quota('registration', ip, limits['registration'], 600)
        elif path.endswith(('/excel/', '/award/', '/certificate/', '/memento/')) or path.startswith('/certificate/'):
            identity = request.user.pk if request.user.is_authenticated else ip
            export = path.endswith('/excel/')
            scope = 'export' if export else 'pdf'
            wait = quota(scope, identity, limits[scope], 60)
        elif path.startswith('/api/') and request.method in ('POST', 'PATCH', 'DELETE'):
            identity = 'user:' + str(request.user.pk) if request.user.is_authenticated else 'ip:' + ip
            scope = 'writes_user' if request.user.is_authenticated else 'writes_guest'
            wait = quota(scope, identity, limits[scope], 60)
        if wait:
            return limited(wait)
        return self.get_response(request)
