from django.db import transaction
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from app.common.http import object_data
from app.accounts.access import require_report_access
from app.models import ClassroomQuiz, ClassroomVersion, RoadSign


def problem(message):
    raise ValidationError({'detail': message})


def clean_text(value, limit):
    if not isinstance(value, str) or len(value) > limit:
        problem(f'Ожидается текст длиной до {limit} символов.')
    return value.strip()


def quiz_content(data, publishing):
    title = clean_text(data.get('title', ''), 160)
    instruction = clean_text(data.get('instruction', ''), 2000)
    rows = data.get('questions', [])
    if not isinstance(rows, list) or len(rows) > 30 or (publishing and not (title and rows)):
        problem('Для запуска нужны название и от 1 до 30 вопросов.')
    questions = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            problem(f'Проверьте вопрос {index}.')
        text = clean_text(row.get('text', ''), 1000)
        options = row.get('options', [])
        if not isinstance(options, list) or len(options) > 6:
            problem(f'Вопрос {index} допускает до шести вариантов.')
        options = [clean_text(option, 500) for option in options]
        correct = row.get('correct')
        if correct is not None and (type(correct) is not int or not 0 <= correct < len(options)):
            problem(f'Проверьте верный вариант в вопросе {index}.')
        if publishing and (not text or len(options) < 2 or not all(options) or correct is None):
            problem(f'Заполните вопрос {index}, от двух до шести ответов и выберите один верный.')
        question = dict(text=text, options=options, correct=correct, explanation=clean_text(row.get('explanation', ''), 1500))
        sign = clean_text(row.get('sign', ''), 50)
        if sign:
            if not RoadSign.objects.filter(slug=sign, is_published=True).exists():
                problem(f'Знак в вопросе {index} больше не доступен. Выберите другой.')
            question['sign'] = sign
        questions.append(question)
    return dict(title=title, instruction=instruction, questions=questions)


def display_questions(questions, review=False):
    signs = {s.slug: s for s in RoadSign.objects.filter(
        is_published=True, slug__in=[q['sign'] for q in questions if q.get('sign')])}
    result = []
    for q in questions:
        item = {'text': q['text'], 'options': q['options']}
        sign = signs.get(q.get('sign'))
        if sign:
            item['image'] = sign.image_url
            item['alt'] = sign.name
        if review:
            item.update(correct=q['correct'], explanation=q['explanation'])
        result.append(item)
    return result


def quiz_card(quiz):
    if hasattr(quiz, 'last_version'):
        number = quiz.last_version
    else:
        number = quiz.versions.aggregate(number=Max('number'))['number']
    return dict(id=quiz.pk, title=quiz.title, ready=quiz.ready, archived=quiz.archived,
                updated_at=quiz.updated_at, revision=quiz.revision, builtin=quiz.owner_id is None,
                last_version=number)


def visible_quizzes(user):
    return ClassroomQuiz.objects.filter(Q(owner=user) | Q(owner__isnull=True))


@never_cache
@api_view(['GET', 'POST'])
def quizzes(request):
    require_report_access(request.user)
    if request.method == 'GET':
        items = visible_quizzes(request.user).annotate(last_version=Max('versions__number')).order_by('-updated_at')
        return Response([quiz_card(q) for q in items])
    content = quiz_content(object_data(request), False)
    quiz = ClassroomQuiz.objects.create(owner=request.user, **content)
    return Response(quiz_card(quiz), status=201)


@never_cache
@api_view(['GET', 'POST', 'DELETE'])
@transaction.atomic
def quiz_detail(request, pk):
    require_report_access(request.user)
    quiz = get_object_or_404(visible_quizzes(request.user).select_for_update(), pk=pk)
    if request.method == 'GET':
        return Response({**quiz_card(quiz), 'instruction': quiz.instruction, 'questions': quiz.questions,
                         'deletable': not quiz.versions.exists()})
    data = object_data(request)
    action = data.get('action')
    if request.method == 'POST' and action == 'copy':
        copy = ClassroomQuiz.objects.create(owner=request.user, title=('Копия · ' + quiz.title)[:160],
                                           instruction=quiz.instruction, questions=quiz.questions)
        return Response(quiz_card(copy), status=201)
    if quiz.owner_id != request.user.pk:
        problem('Готовый тест можно скопировать в свои тесты.')
    if data.get('revision') != quiz.revision:
        return Response({'detail': 'Тест изменён в другой вкладке. Обновите страницу.'}, status=409)
    if request.method == 'DELETE':
        if quiz.versions.exists():
            problem('Готовую версию можно отправить в архив.')
        quiz.delete()
        return Response(status=204)
    if action in ('archive', 'restore'):
        quiz.archived = action == 'archive'
    elif action in ('save', 'publish') and not quiz.archived:
        content = quiz_content(data, action == 'publish')
        for field, value in content.items():
            setattr(quiz, field, value)
        quiz.ready = action == 'publish'
        if quiz.ready:
            last = quiz.versions.order_by('-number').first()
            if not last or any(getattr(last, field) != value for field, value in content.items()):
                ClassroomVersion.objects.create(quiz=quiz, number=last.number + 1 if last else 1, **content)
    else:
        problem('Это действие сейчас недоступно.')
    quiz.revision += 1
    quiz.save()
    return Response(quiz_card(quiz))
