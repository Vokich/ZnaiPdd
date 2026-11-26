from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.accounts.access import is_child
from app.common.http import checked, object_data
from app.documents.certificates import award_download
from app.models import TestResult
from app.quizzes.forms import AdultPddTestForm, JuniorPddTestForm, TeenPddTestForm
from app.reporting.records import save_age_result


TEST_FORMS = {
    TestResult.TestType.JUNIOR: JuniorPddTestForm,
    TestResult.TestType.TEEN: TeenPddTestForm,
    TestResult.TestType.ADULT: AdultPddTestForm,
}


def result_data(result):
    return {
        'id': result.pk,
        'test_type': result.test_type,
        'score': result.score,
        'total': result.total_questions,
        'passing_score': result.passing_score,
        'passed': result.passed,
        'earns_diploma': result.earns_diploma,
        'completed_at': result.completed_at,
    }


def result_page(user, before):
    rows = user.test_results.order_by('-pk')
    if before:
        if not before.isascii() or not before.isdecimal() or len(before) > 18:
            raise ValidationError({'detail': 'Неверная страница результатов.'})
        rows = rows.filter(pk__lt=int(before))
    batch = list(rows[:6])
    return {'results': [result_data(row) for row in batch[:5]], 'next': batch[4].pk if len(batch) > 5 else None}


@never_cache
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def result_history(request):
    if not is_child(request.user):
        raise PermissionDenied('История возрастных тестов доступна ученикам.')
    return Response(result_page(request.user, request.query_params.get('before')))


def selected_result(request, results):
    result_id = request.query_params.get('id')
    if result_id is not None:
        if not result_id.isascii() or not result_id.isdecimal() or len(result_id) > 18:
            raise NotFound()
        results = results.filter(pk=result_id)
    return results.order_by('-completed_at', '-pk').first()


@never_cache
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test(request, test_type):
    if not is_child(request.user):
        return Response({'detail': 'Тесты доступны школьникам.'}, status=403)
    form_class = TEST_FORMS.get(test_type)
    if form_class is None:
        raise NotFound()
    form = form_class()
    if not form.questions_data:
        raise NotFound('В этом тесте пока нет вопросов.')
    # Older clients submit only answers. Keep the revision served to that session.
    revision_key = f'age_test_revision_{test_type}'
    if request.session.get(revision_key) != form.revision:
        request.session[revision_key] = form.revision
    return Response({
        'passing_score': form.passing_score,
        'revision': form.revision,
        'questions': [
            {'id': question['id'], 'text': question['text'], 'options': question['options']}
            for question in form.questions_data
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

    payload = object_data(request)
    answers = payload.get('answers')
    if not isinstance(answers, dict):
        raise ValidationError({'answers': ['Укажите ответы на вопросы.']})
    form = form_class({f'question_{key}': value for key, value in answers.items()})
    revision = payload.get('revision', request.session.get(f'age_test_revision_{test_type}'))
    if form.questions_data and revision != form.revision:
        return Response({'detail': 'Тест изменился. Обновите страницу, чтобы открыть новую версию.'}, status=409)
    result = save_age_result(request.user, checked(form))
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
    if result is None or result.score < result.passing_score:
        raise NotFound('Сначала успешно сдайте тест.')
    return award_download(result)
