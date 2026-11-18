from datetime import timedelta
from secrets import randbelow

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.cache import never_cache
from reportlab.graphics import renderSVG
from reportlab.graphics.barcode import createBarcodeDrawing
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, Throttled
from rest_framework.response import Response

from .api import object_data, organization_data, require_report_access
from .classroom_lessons import LESSONS, explain, lesson_card, presentation, run_title
from .classroom_quizzes import display_questions, problem, visible_quizzes
from .models import ClassroomAttempt, ClassroomRun


def counts(run):
    return run.attempts.aggregate(connected=Count('id'), started=Count('id', filter=Q(started=True)),
                                  submitted=Count('score'))


def close_run(run, when):
    if run.closed_at:
        return
    questions = run.version.questions
    summary = counts(run)
    correct = [0] * len(questions)
    for answers in run.attempts.filter(score__isnull=False).values_list('answers', flat=True):
        for index, question in enumerate(questions):
            correct[index] += answers[index] == question['correct']
    summary.update(correct=correct, average=sum(correct) / summary['submitted'] if summary['submitted'] else None)
    run.summary = summary
    run.closed_at = when
    run.review_until = when + timedelta(hours=settings.CLASSROOM_REVIEW_HOURS)
    run.accepting = False
    run.save(update_fields=['summary', 'closed_at', 'review_until', 'accepting'])
    run.attempts.filter(score__isnull=True).delete()


def refresh_run(run):
    now = timezone.now()
    if run.deadline and run.deadline <= now and not run.closed_at:
        close_run(run, run.deadline)
    if run.review_until and run.review_until <= now:
        run.attempts.all().delete()


def status(run):
    if run.closed_at:
        return 'closed'
    return 'running' if run.started_at else 'waiting'


def run_card(run):
    report = getattr(run, 'report', None)
    return {'id': run.pk, 'title': run_title(run), 'lesson': run.lesson, 'code': run.code,
            'version': run.version.number if run.version_id else None, 'opened_at': run.opened_at,
            'state': status(run), 'accepting': run.accepting, 'deadline': run.deadline,
            'report_id': report.pk if report else None}


def teacher_detail(user, run):
    profile = user.profile
    data = {**run_card(run), 'date': timezone.localdate(run.started_at or run.opened_at),
            'organization': organization_data(profile.organization) if profile.organization_id else None}
    if run.lesson:
        data['steps'] = presentation(run.lesson)
    else:
        data['counts'] = {k: run.summary[k] for k in ('connected', 'started', 'submitted')} if run.closed_at else counts(run)
        if run.closed_at:
            data['summary'] = {**run.summary, 'questions': [q['text'] for q in run.version.questions]}
    return data


@never_cache
@api_view(['GET', 'POST'])
def classroom(request):
    require_report_access(request.user)
    if request.method == 'GET':
        runs = ClassroomRun.objects.filter(owner=request.user).select_related('version', 'report').order_by('-opened_at')
        history = []
        for run in runs:
            if run.deadline and not run.closed_at and run.deadline <= timezone.now():
                with transaction.atomic():
                    run = ClassroomRun.objects.select_for_update().get(pk=run.pk)
                    refresh_run(run)
            history.append(run_card(run))
        return Response({'lessons': [lesson_card(key) for key in LESSONS], 'history': history})

    data = object_data(request)
    with transaction.atomic():
        if 'lesson' in data:
            lesson = data['lesson']
            if not isinstance(lesson, str) or lesson not in LESSONS:
                problem('Выберите готовый урок.')
            run = ClassroomRun.objects.create(owner=request.user, lesson=lesson, started_at=timezone.now())
        else:
            pk = data.get('quiz')
            if type(pk) is not int or not 0 < pk < 2**63:
                problem('Выберите тест для запуска.')
            quiz = get_object_or_404(visible_quizzes(request.user).select_for_update(), pk=pk, archived=False)
            version = quiz.versions.order_by('-number').first()
            if not version:
                problem('Сначала сохраните готовую версию теста.')
            for _ in range(5):
                try:
                    with transaction.atomic():
                        run = ClassroomRun.objects.create(owner=request.user, version=version,
                            code=f'{randbelow(10**8):08}', deadline=timezone.now() + timedelta(minutes=20))
                    break
                except IntegrityError:
                    continue
            else:
                problem('Не удалось создать код. Повторите запуск.')
    return Response(run_card(run), status=201)


@never_cache
@api_view(['GET', 'POST'])
@transaction.atomic
def teacher_run(request, pk):
    require_report_access(request.user)
    run = get_object_or_404(ClassroomRun.objects.select_for_update(), pk=pk, owner=request.user)
    refresh_run(run)
    if request.method == 'POST':
        data = object_data(request)
        if run.lesson:
            return Response(explain(run.lesson, data.get('step'), data.get('answer')))
        action = data.get('action')
        if action == 'close':
            close_run(run, timezone.now())
        elif run.closed_at:
            problem('Сессия уже закрыта.')
        elif action == 'start':
            if not run.started_at:
                run.started_at = timezone.now()
                run.deadline = run.started_at + timedelta(minutes=20)
                run.save(update_fields=['started_at', 'deadline'])
        elif action == 'lock':
            run.accepting = False
            run.save(update_fields=['accepting'])
        else:
            problem('Неизвестное действие.')
    return Response(teacher_detail(request.user, run))


@never_cache
@api_view(['GET'])
def qr_image(request, pk):
    require_report_access(request.user)
    run = get_object_or_404(ClassroomRun, pk=pk, owner=request.user, code__isnull=False)
    url = request.build_absolute_uri('/join/' + run.code + '/')
    drawing = createBarcodeDrawing('QR', value=url, width=300, height=300, barLevel='M')
    return HttpResponse(renderSVG.drawToString(drawing), content_type='image/svg+xml')


def browser_key(request, run):
    key = request.session.get('classroom_browser')
    if not key:
        if not request.session.session_key:
            request.session.create()
        key = salted_hmac('class-browser', request.session.session_key).hexdigest()
        request.session['classroom_browser'] = key
    return salted_hmac(str(run.pk), key).hexdigest()


def join_code(request, code):
    # Count unsuccessful lookups only: a whole classroom can share one address.
    address = request.META.get('REMOTE_ADDR', '')
    if settings.SECURE_PROXY_SSL_HEADER:
        address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[-1].strip() or address
    key = 'class-code:' + salted_hmac('class-code', address).hexdigest()
    if cache.get(key, 0) >= 18:
        raise Throttled(60)
    run = ClassroomRun.objects.select_for_update().filter(code=code).first()
    if run is None:
        if not cache.add(key, 1, 60):
            try:
                cache.incr(key)
            except ValueError:
                cache.add(key, 1, 60)
        raise NotFound('Проверьте код занятия.')
    return run


def participant_data(run, attempt):
    data = dict(title=run_title(run), state=status(run), accepting=run.accepting, deadline=run.deadline,
                joined=bool(attempt), started=False, submitted=False, review_until=run.review_until)
    if not attempt:
        return data
    data.update(started=attempt.started, submitted=attempt.score is not None, revision=attempt.revision,
                answers=attempt.answers)
    review = bool(run.closed_at and attempt.score is not None)
    if attempt.started and (review or (not run.closed_at and attempt.score is None)):
        data.update(questions=display_questions(run.version.questions, review), instruction=run.version.instruction)
    if review:
        data['score'] = attempt.score
    return data


@never_cache
@api_view(['GET', 'POST'])
@transaction.atomic
def participant(request, code):
    run = join_code(request, code)
    refresh_run(run)
    browser = browser_key(request, run)
    attempt = run.attempts.filter(browser=browser).first()
    if request.method == 'GET':
        return Response(participant_data(run, attempt))
    data = object_data(request)
    action = data.get('action')
    if action == 'join' and not attempt:
        if not run.accepting or run.closed_at:
            problem('Подключение к этому занятию закрыто.')
        attempt, _ = ClassroomAttempt.objects.get_or_create(run=run, browser=browser)
    if not attempt:
        problem('Сначала присоединитесь к занятию.')
    if action == 'join' or (action == 'submit' and attempt.score is not None):
        return Response(participant_data(run, attempt))
    if status(run) != 'running' or attempt.score is not None:
        problem('Приём ответов сейчас закрыт.')
    if action == 'begin':
        if not attempt.started:
            attempt.started = True
            attempt.answers = [None] * len(run.version.questions)
            attempt.save(update_fields=['started', 'answers'])
    elif action in ('save', 'submit') and attempt.started:
        revision = data.get('revision')
        if type(revision) is not int or revision != attempt.revision:
            return Response({'detail': 'Черновик изменён. Загрузите сохранённые ответы.'}, status=409)
        answers = data.get('answers')
        questions = run.version.questions
        if not isinstance(answers, list) or len(answers) != len(questions):
            problem('Проверьте ответы на вопросы.')
        for value, q in zip(answers, questions):
            if value is None and action == 'save':
                continue
            if type(value) is not int or not 0 <= value < len(q['options']):
                problem('Выберите один ответ на каждый вопрос.')
        attempt.answers = answers
        attempt.revision += 1
        if action == 'submit':
            attempt.score = sum(value == q['correct'] for value, q in zip(answers, questions))
        attempt.save(update_fields=['revision', 'answers', 'score'])
    else:
        problem('Откройте вопросы теста.')
    return Response(participant_data(run, attempt))
