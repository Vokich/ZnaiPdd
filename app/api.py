from datetime import date
from io import BytesIO
from random import shuffle

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import F
from django.forms import DateField
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
from .models import Certificate, Profile, RoadSign, TestResult, UserSignProgress
from .municipalities import search_municipalities
from .views import download_training_file, is_child, is_teacher


TEST_FORMS = {
    TestResult.TestType.JUNIOR: JuniorPddTestForm,
    TestResult.TestType.TEEN: TeenPddTestForm,
    TestResult.TestType.ADULT: AdultPddTestForm,
}
PROFILE_FIELDS = ('surname1', 'name', 'surname2', 'school', 'birth_date', 'region', 'position')
PASSING_SCORE = 18
DIPLOMA_SCORE = 24


def user_data(user):
    if not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    return {
        'id': user.pk,
        'username': user.username,
        'name': profile.name if profile else user.username,
        'role': profile.role if profile else None,
    }


def profile_data(user):
    profile = get_object_or_404(Profile, user=user)
    return {
        **user_data(user),
        **{field: getattr(profile, field) for field in PROFILE_FIELDS},
        'email': user.email,
        'age': profile.age,
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
        'children_count': report.children_count,
        'photo_link': report.photo_link,
    }


def sign_data(sign, unlocked):
    return {
        'slug': sign.slug,
        'category': sign.category,
        'category_label': sign.get_category_display(),
        'unlocked': unlocked,
        'name': sign.name if unlocked else None,
        'image': sign.image.url if unlocked and sign.image else None,
        'description': (sign.full_description or sign.short_description) if unlocked else None,
        'fun_fact': sign.fun_fact if unlocked else None,
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
        with transaction.atomic():
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


@never_cache
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    if request.method == 'PATCH':
        data = object_data(request)
        current = get_object_or_404(Profile, user=request.user)
        fields = {field: getattr(current, field) for field in PROFILE_FIELDS}
        fields.update(username=request.user.username, email=request.user.email)
        fields.update({key: data[key] for key in fields if key in data})
        form = checked(UserProfileForm(fields, instance=request.user, profile_instance=current))
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            if User.objects.exclude(pk=request.user.pk).filter(username=form.cleaned_data['username']).exists():
                raise ValidationError({'username': ['Пользователь с таким логином уже существует.']})
            raise
    user = request.user
    return Response({
        'profile': profile_data(user),
        'results': [result_data(result) for result in user.test_results.all()] if is_child(user) else [],
        'reports_count': user.lesson_reports.count() if is_teacher(user) else 0,
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
    category = request.query_params.get('category')
    signs = RoadSign.objects.filter(category=category) if category else RoadSign.objects.all()
    unlocked_ids = set()
    if request.user.is_authenticated:
        unlocked_ids = set(request.user.sign_progress.filter(unlocked=True).values_list('sign_id', flat=True))
    return Response({
        'categories': [{'value': value, 'label': label} for value, label in RoadSign.Category.choices],
        'total': RoadSign.objects.count(),
        'unlocked_count': len(unlocked_ids),
        'signs': [sign_data(sign, sign.pk in unlocked_ids) for sign in signs],
    })


@never_cache
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sign(request, slug):
    sign = get_object_or_404(RoadSign, slug=slug)
    unlocked = request.user.sign_progress.filter(sign=sign, unlocked=True).exists()
    return Response(sign_data(sign, unlocked))


@never_cache
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sign_test(request, slug):
    sign = get_object_or_404(RoadSign, slug=slug)
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
    progress, _ = UserSignProgress.objects.get_or_create(user=request.user, sign=sign)
    UserSignProgress.objects.filter(pk=progress.pk, unlocked=False).update(
        unlocked=True, test_passed_at=timezone.now(),
    )
    return Response({'unlocked': True})


@never_cache
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def lesson_reports(request):
    if not is_teacher(request.user):
        return Response({'detail': 'Отчёты доступны педагогам.'}, status=403)
    if request.method == 'GET':
        return Response([report_data(report) for report in request.user.lesson_reports.all()])
    report = checked(TeacherLessonReportForm(object_data(request))).save(commit=False)
    report.user = request.user
    report.save()
    return Response(report_data(report), status=201)


@api_view(['GET'])
def training_material(request):
    return download_training_file(request)
