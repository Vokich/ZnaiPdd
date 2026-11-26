from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Case, Value, When
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.accounts.access import account_role, can_submit_lesson_reports, is_child
from app.accounts.forms import LoginForm, PasswordChangeForm, UserProfileForm, UserRegistrationForm
from app.common.http import checked, object_data
from app.organizations.api import organization_data
from app.practice.service import exercise_card, public_exercises
from app.quizzes.api import result_page
from app.rankings.scores import rating_overview


def user_data(user):
    if not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    return {
        'id': user.pk,
        'username': user.username,
        'name': (profile.name or user.username) if profile else user.username,
        'role': account_role(user),
        'can_submit_reports': can_submit_lesson_reports(user),
    }


def profile_data(user):
    profile = getattr(user, 'profile', None)
    organization = profile.organization if profile else None
    municipality = profile.municipality if profile else None
    return {
        **user_data(user),
        'surname1': profile.surname1 if profile else '',
        'name': profile.name if profile else '',
        'surname2': profile.surname2 if profile else '',
        'school': profile.school if profile else '',
        'region': municipality.name if municipality else (profile.region if profile else ''),
        'position': profile.position if profile else '',
        'organization': organization_data(organization) if organization else None,
        'organization_confirmed': bool(profile and profile.organization_confirmed),
        'competition_enabled': profile.competition_enabled if profile else False,
        'email': user.email,
    }


@never_cache
@ensure_csrf_cookie
@api_view(['GET', 'POST', 'DELETE'])
def session(request):
    if request.method == 'DELETE':
        logout(request._request)
        return Response(status=204)
    user = request.user
    if request.method == 'POST':
        credentials = checked(LoginForm(object_data(request))).cleaned_data
        user = authenticate(request._request, **credentials)
        if user is None:
            raise ValidationError({'detail': 'Неверный логин или пароль.'})
        login(request._request, user)
    return Response({'user': user_data(user)})


@never_cache
@api_view(['POST'])
def register(request):
    data = object_data(request)
    if data.get('consent') is not True:
        raise ValidationError({'consent': ['Подтвердите согласие на обработку персональных данных.']})
    form = checked(UserRegistrationForm(data))
    try:
        user = form.save()
    except IntegrityError:
        if User.objects.filter(username=form.cleaned_data['username']).exists():
            raise ValidationError({'username': ['Пользователь с таким логином уже существует.']})
        raise
    login(request._request, user, backend='django.contrib.auth.backends.ModelBackend')
    return Response({'user': user_data(user)}, status=201)


@never_cache
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user
    if request.method == 'PATCH':
        data = object_data(request)
        if 'organization' in data:
            raise PermissionDenied('Организацию подтверждает администратор по личному обращению.')
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=user.pk)
                current = getattr(user, 'profile', None)
                form = UserProfileForm(instance=user, profile_instance=current)
                fields = {
                    name: data.get(name, field.prepare_value(form.initial.get(name)))
                    for name, field in form.fields.items()
                }
                user = checked(UserProfileForm(fields, instance=user, profile_instance=current)).save()
        except IntegrityError:
            if User.objects.exclude(pk=request.user.pk).filter(username=fields['username']).exists():
                raise ValidationError({'username': ['Пользователь с таким логином уже существует.']})
            raise
    data = profile_data(user)
    suggestions = public_exercises().select_related('published_version').order_by(
        Case(When(slug='cross-on-green', then=Value(0)), When(slug='stop-calendar', then=Value(1)), default=Value(2)),
        'title',
    )[:2]
    first = result_page(user, None) if is_child(user) else {'results': [], 'next': None}
    return Response({
        'profile': data,
        'results': first['results'], 'next_results': first['next'],
        'reports_count': user.lesson_reports.count() if data['can_submit_reports'] else 0,
        'rating': rating_overview(user.pk),
        'suggested_practice': [exercise_card(exercise) for exercise in suggestions],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def password(request):
    user = checked(PasswordChangeForm(object_data(request), user=request.user)).save()
    update_session_auth_hash(request._request, user)
    return Response(status=204)
