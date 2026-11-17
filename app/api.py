from datetime import date
from io import BytesIO
from random import shuffle

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Case, F, Value, When
from django.forms import DateField
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .access import account_role, can_submit_lesson_reports, is_child
from .certificate_generator import CertificateGenerator
from .forms import (
    AdultPddTestForm,
    JuniorPddTestForm,
    LoginForm,
    PasswordChangeForm,
    TeacherLessonReportForm,
    TeenPddTestForm,
    UserProfileForm,
    UserRegistrationForm,
)
from .models import Certificate, Organization, RoadSign, TeacherLessonReport, TestResult
from .municipalities import search_municipalities
from .practice import exercise_card, public_exercises, related_exercises
from .rating import rating_overview
from .route_levels import LEVELS
from .sign_catalog import catalog_signs, learned_sign_ids, mark_sign_learned, published_signs
from .views import download_training_file


TEST_FORMS = {
    TestResult.TestType.JUNIOR: JuniorPddTestForm,
    TestResult.TestType.TEEN: TeenPddTestForm,
    TestResult.TestType.ADULT: AdultPddTestForm,
}
PASSING_SCORE = 18
DIPLOMA_SCORE = 24


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
        'competition_enabled': profile.competition_enabled if profile else False,
        'email': user.email,
    }


def checked(form):
    errors = {}
    for name, field in form.fields.items():
        value = form.data.get(name)
        if isinstance(field, DateField) and value is not None and not isinstance(value, (date, str)):
            errors[name] = [field.error_messages['invalid']]
        elif isinstance(value, (dict, list)):
            errors[name] = ['Укажите одно значение.']
    if errors:
        raise ValidationError(errors)
    if not form.is_valid():
        raise ValidationError(form.errors)
    return form


def object_data(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'detail': 'Ожидается объект JSON.'})
    return request.data


def result_data(result):
    return {
        'id': result.pk,
        'test_type': result.test_type,
        'score': result.score,
        'total': result.total_questions,
        'passing_score': result.passing_score,
        'passed': result.passed,
        'completed_at': result.completed_at,
    }


def selected_result(request, results):
    result_id = request.query_params.get('id')
    if result_id is not None:
        if not result_id.isascii() or not result_id.isdecimal() or len(result_id) > 18:
            raise NotFound()
        results = results.filter(pk=result_id)
    return results.order_by('-completed_at', '-pk').first()


def report_data(report):
    return {
        'id': report.pk,
        'lesson_date': report.lesson_date,
        'location': report.location,
        'participants_count': report.participants_count,
        'route_level': report.route_level,
        'practice': {'id': report.practice_id, 'title': report.practice.title, 'slug': report.practice.slug}
                     if report.practice else None,
        'completed_count': report.completed_count,
        'organization': organization_data(report.organization) if report.organization else None,
    }


def organization_data(organization):
    return {'id': organization.pk, 'name': organization.name, 'municipality': organization.municipality.name}


def sign_data(sign, unlocked):
    return {
        'slug': sign.slug,
        'category': sign.category,
        'category_label': sign.get_category_display(),
        'unlocked': unlocked,
        'number': sign.number,
        'name': sign.name,
        'image': sign.image_url,
        'description': sign.full_description or sign.short_description,
        'fun_fact': sign.fun_fact,
        'source_url': sign.source_url,
        'image_credit': sign.image_credit,
        'has_test': sign.has_test,
    }


@api_view(['GET'])
def health(request):
    return Response({'status': 'ok'})


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


@api_view(['GET'])
def municipalities(request):
    results, more = search_municipalities(request.query_params.get('q', ''))
    return Response({'results': results, 'more': more})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organizations(request):
    query = request.query_params.get('q', '').strip()
    if not 2 <= len(query) <= 300:
        return Response([])
    organizations = Organization.objects.filter(name__icontains=query).select_related('municipality')[:30]
    return Response([organization_data(organization) for organization in organizations])


@never_cache
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user
    if request.method == 'PATCH':
        data = object_data(request)
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
    return Response({
        'profile': data,
        'results': [result_data(result) for result in user.test_results.all()] if is_child(user) else [],
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test(request, test_type):
    if not is_child(request.user):
        return Response({'detail': 'Тесты доступны школьникам.'}, status=403)
    form_class = TEST_FORMS.get(test_type)
    if form_class is None:
        raise NotFound()
    questions = form_class().questions_data
    return Response({
        'passing_score': PASSING_SCORE,
        'questions': [
            {'id': question['id'], 'text': question['text'], 'options': question['options']}
            for question in questions
        ],
    })


@never_cache
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def test_results(request, test_type):
    if not is_child(request.user):
        return Response({'detail': 'Тесты доступны школьникам.'}, status=403)
    form_class = TEST_FORMS.get(test_type)
    if form_class is None:
        raise NotFound()
    if request.method == 'GET':
        result = selected_result(request, request.user.test_results.filter(test_type=test_type))
        if result is None:
            raise NotFound('Для этого теста пока нет результата.')
        return Response(result_data(result))

    answers = object_data(request).get('answers')
    if not isinstance(answers, dict):
        raise ValidationError({'answers': ['Укажите ответы на вопросы.']})
    form = checked(form_class({f'question_{key}': value for key, value in answers.items()}))
    score = form.check_answers(passing_score=PASSING_SCORE)
    result = TestResult.objects.create(
        user=request.user,
        test_type=test_type,
        score=score['score'],
        total_questions=score['total'],
        passing_score=score['passing_score'],
        passed=score['passed'],
    )
    return Response(result_data(result), status=201)


@never_cache
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def certificate(request, test_type):
    if not is_child(request.user):
        return Response({'detail': 'Сертификаты доступны школьникам.'}, status=403)
    if test_type not in TEST_FORMS:
        raise NotFound()
    result = selected_result(request, request.user.test_results.filter(test_type=test_type, passed=True))
    if result is None or result.score < PASSING_SCORE:
        raise NotFound('Сначала успешно сдайте тест.')
    document_type = Certificate.DocumentType.DIPLOMA if result.score >= DIPLOMA_SCORE else Certificate.DocumentType.CERTIFICATE
    pdf = CertificateGenerator(request.user, test_type, document_type).generate()
    with transaction.atomic():
        certificate, _ = Certificate.objects.get_or_create(
            user=request.user, test_type=test_type, document_type=document_type,
            defaults={'test_result': result},
        )
        Certificate.objects.filter(pk=certificate.pk).update(
            test_result=result, download_count=F('download_count') + 1,
        )
    filename = f'{document_type.label}_{request.user.profile.full_name}.pdf'
    return FileResponse(BytesIO(pdf), as_attachment=True, filename=filename, content_type='application/pdf')


@never_cache
@api_view(['GET'])
def signs(request):
    signs = catalog_signs(request.query_params.get('category', ''), request.query_params.get('q', ''))
    unlocked_ids = learned_sign_ids(request.user)
    return Response({
        'categories': [{'value': value, 'label': label} for value, label in RoadSign.Category.choices],
        'total': published_signs().count(),
        'unlocked_count': len(unlocked_ids),
        'signs': [sign_data(sign, sign.pk in unlocked_ids) for sign in signs],
    })


@never_cache
@api_view(['GET'])
def sign(request, slug):
    sign = get_object_or_404(published_signs(), slug=slug)
    unlocked = request.user.is_authenticated and request.user.sign_progress.filter(sign=sign, unlocked=True).exists()
    return Response({
        **sign_data(sign, unlocked),
        'exercises': list(related_exercises(sign).values('slug', 'title')),
    })


@never_cache
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sign_test(request, slug):
    sign = get_object_or_404(published_signs(), slug=slug)
    if not sign.has_test:
        raise NotFound('Для этого знака пока нет мини-теста.')
    if request.user.sign_progress.filter(sign=sign, unlocked=True).exists():
        return Response({'unlocked': True})
    if request.method == 'GET':
        options = [{'id': index, 'text': text} for index, text in enumerate(sign.answer_options, start=1)]
        shuffle(options)
        return Response({'unlocked': False, 'question': sign.question, 'options': options})
    answer = object_data(request).get('answer')
    if type(answer) is not int or not 1 <= answer <= len(sign.answer_options):
        raise ValidationError({'answer': ['Выберите вариант ответа.']})
    if answer != sign.correct_answer:
        raise ValidationError({'answer': ['Неверный ответ. Попробуйте ещё раз.']})
    mark_sign_learned(request.user, sign)
    return Response({'unlocked': True})


def require_report_access(user):
    if not can_submit_lesson_reports(user):
        raise PermissionDenied('Право на отчёты выдаёт администратор после проверки учётной записи.')


@never_cache
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lesson_report_options(request):
    require_report_access(request.user)
    routes = [{'id': key, 'title': level['title']} for key, level in LEVELS.items()]
    if request.query_params.get('include') == 'practice':
        return Response({'routes': routes, 'practice': list(public_exercises().values('id', 'slug', 'title'))})
    return Response(routes)


@never_cache
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def lesson_reports(request):
    require_report_access(request.user)
    if request.method == 'GET':
        reports = request.user.lesson_reports.select_related('organization__municipality', 'practice')
        return Response([report_data(report) for report in reports])
    report = checked(TeacherLessonReportForm(object_data(request))).save(commit=False)
    report.user = request.user
    report.save()
    return Response(report_data(report), status=201)


@never_cache
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def lesson_report(request, report_id):
    require_report_access(request.user)
    reports = request.user.lesson_reports.select_related('organization__municipality', 'practice')
    if request.method == 'GET':
        return Response(report_data(get_object_or_404(reports, pk=report_id)))
    data = object_data(request).copy()
    with transaction.atomic():
        report = get_object_or_404(TeacherLessonReport.objects.select_for_update(), user=request.user, pk=report_id)
        for field in ('lesson_date', 'location', 'participants_count', 'route_level'):
            data.setdefault(field, getattr(report, field))
        data.setdefault('practice', report.practice_id)
        data.setdefault('completed_count', report.completed_count if data['route_level'] or data['practice'] else None)
        data.setdefault('organization', report.organization_id)
        report = checked(TeacherLessonReportForm(data, instance=report)).save()
    return Response(report_data(report))


@api_view(['GET'])
def training_material(request):
    return download_training_file(request)
