from datetime import timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, parser_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.response import Response

from .api import object_data
from .models import RouteProgress, RouteResult
from .route_pdf import route_pdf
from .route_levels import LEVELS
from .safe_routes import VERSION, apply_choice, pending_rule, restore_route, route_data, rule_url, start_route


SESSION_KEY = 'safe_route'


def guest_route(request):
    state = request.session.get(SESSION_KEY)
    if state and state['expires'] > timezone.now().timestamp():
        return restore_route(state)
    return None


def saved_route(user):
    return restore_route(RouteProgress.objects.filter(user=user).values_list('state', flat=True).first())


def available(state):
    return state is not None and state['version'] in (1, VERSION)


def route_with_result(state, user):
    data = route_data(state)
    if data['completed'] and user and user.is_authenticated:
        saved = RouteResult.objects.filter(user=user, attempt=state['id']).values('score', 'mistakes').first()
        if saved:
            data.update(saved)
    return data


def response_data(state, guest=None, *, user=None):
    return {
        'levels': [{'id': key, **level} for key, level in LEVELS.items()],
        'route': route_with_result(state, user) if available(state) else None,
        'older_version': state is not None and not available(state),
        'guest_route': route_data(guest) if available(guest) else None,
    }


@never_cache
@ensure_csrf_cookie
@api_view(['GET', 'POST'])
@parser_classes([JSONParser, FormParser])
def route_progress(request):
    user = request.user
    guest = guest_route(request)
    if request.method == 'GET':
        return Response(response_data(saved_route(user), guest, user=user) if user.is_authenticated else response_data(guest))

    data = object_data(request)
    redirect = None
    with transaction.atomic():
        if user.is_authenticated:
            User.objects.select_for_update().only('pk').get(pk=user.pk)
        state = saved_route(user) if user.is_authenticated else guest
        action = data.get('action')
        if action == 'start':
            level = data.get('level')
            if not isinstance(level, str) or level not in LEVELS:
                raise ValidationError({'detail': 'Выбери один из уровней.'})
            state = start_route(level)
        elif action == 'attach':
            if not user.is_authenticated:
                raise PermissionDenied('Войди, чтобы сохранить маршрут в кабинете.')
            if not available(guest) or guest['id'] != data.get('id'):
                raise NotFound('Гостевой маршрут больше недоступен.')
            state = guest.copy()
            state.pop('expires')
            request.session.pop(SESSION_KEY)
            guest = None
        elif action in ('move', 'open-rule'):
            if not available(state) or state['id'] != data.get('id'):
                raise NotFound('Этот маршрут больше недоступен.')
            revision = data.get('revision')
            if action == 'open-rule':
                if str(revision) != str(state['revision']):
                    return Response({'detail': 'Маршрут обновился. Открой правило ещё раз.'}, status=409)
                feedback = state['feedback']
                if not feedback or feedback['accepted']:
                    raise ValidationError({'detail': 'На этом участке сейчас нет ошибки для разбора.'})
                event = state['mistake_events'][-1]
                if not event['opened_at']:
                    event['opened_at'] = timezone.now().isoformat()
                redirect = HttpResponseRedirect(rule_url(event['rule']), status=303)
                redirect['Referrer-Policy'] = 'no-referrer'
            else:
                option = data.get('choice')
                if type(revision) is not int or not isinstance(option, str):
                    raise ValidationError({'detail': 'Выбери действие на текущем участке.'})
                if revision == state['revision'] - 1 and option == state['last_choice']:
                    return Response(response_data(state, guest if user.is_authenticated else None, user=user))
                if revision != state['revision']:
                    return Response({'detail': 'Маршрут обновился. Открой его ещё раз.'}, status=409)
                if pending_rule(state):
                    raise PermissionDenied('Открой пункт ПДД, чтобы исправить ошибку.')
                if not apply_choice(state, option):
                    raise ValidationError({'detail': 'Это действие недоступно на текущем участке.'})
        else:
            raise ValidationError({'detail': 'Неизвестное действие с маршрутом.'})

        if user.is_authenticated:
            if state['version'] == VERSION and state['path'][-1] == 'school':
                result = route_data(state)
                record, _ = RouteResult.objects.get_or_create(attempt=state['id'], defaults={
                    'user': user, 'level': state['level'], 'score': result['score'], 'total': result['total'],
                    'mistakes': result['mistakes'], 'rule_reviews': state['mistake_events'],
                })
                if record.user_id != user.pk:
                    raise PermissionDenied('Этот маршрут уже сохранён в другом кабинете.')
            RouteProgress.objects.update_or_create(user=user, defaults={'state': state})
        else:
            state.setdefault('expires', (timezone.now() + timedelta(hours=2)).timestamp())
            request.session[SESSION_KEY] = state
    return redirect if redirect is not None else Response(response_data(state, guest if user.is_authenticated else None, user=user))


@never_cache
@api_view(['GET'])
def route_memento(request, attempt):
    state = saved_route(request.user) if request.user.is_authenticated else guest_route(request)
    if not available(state) or state['id'] != attempt or state['path'][-1] != 'school':
        raise NotFound()
    return route_pdf(state, route_with_result(state, request.user))
