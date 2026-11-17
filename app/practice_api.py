from itertools import permutations
from random import shuffle

from django.core.exceptions import ValidationError as ModelValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .api import object_data
from .media import gallery_data, image_response
from .models import PracticeExercise, PracticeImage, PracticeResult, PracticeVersion
from .practice import check_practice, exercise_card, public_exercises, public_versions


GUEST_RESULTS = 'practice_completions'


def sign_link(sign):
    if sign is None or not sign.is_published:
        return None
    return {'slug': sign.slug, 'name': sign.name, 'number': sign.number, 'image': sign.image_url}


def items(texts):
    return [{'id': index, 'text': text} for index, text in enumerate(texts, start=1)]


def guest_completions(request):
    cutoff = timezone.now().timestamp() - 7200
    return {key: date for key, date in request.session.get(GUEST_RESULTS, {}).items() if date > cutoff}


def exercise_data(request, version, preview):
    exercise = version.exercise
    data = version.content
    result = False
    if not preview:
        if request.user.is_authenticated:
            result = request.user.practice_results.filter(version=version).exists()
        else:
            result = str(version.pk) in guest_completions(request)
    response = {
        'title': exercise.title, 'kind': version.kind, 'version': version.pk,
        'prompt': version.prompt, 'completed': result, 'preview': preview,
        'sign': sign_link(version.sign),
        'images': gallery_data(version.images.all()),
    }
    if version.kind == PracticeVersion.Kind.ORDER:
        cards = items(data.get('cards', []))
        shuffle(cards)
        accepted = {tuple(order) for order in data.get('orders', [])}
        if tuple(card['id'] for card in cards) in accepted:
            for ordering in permutations(cards):
                if tuple(card['id'] for card in ordering) not in accepted:
                    cards = list(ordering)
                    break
        response['cards'] = cards
    else:
        response.update({
            'meanings': items(data.get('meanings', [])), 'conditions': items(data.get('conditions', [])),
            'plates': [sign_link(version.plate_a), sign_link(version.plate_b)],
        })
    return response


@never_cache
@api_view(['GET'])
def exercises(request):
    qs = public_exercises().select_related('published_version')
    topic = request.query_params.get('topic', '')
    difficulty = request.query_params.get('difficulty', '')
    if topic:
        qs = qs.filter(topic=topic)
    if difficulty:
        qs = qs.filter(difficulty=difficulty)
    return Response({
        'items': [exercise_card(exercise) for exercise in qs],
        'topics': [{'id': key, 'label': label} for key, label in PracticeExercise.Topic.choices],
        'difficulties': [{'id': key, 'label': label} for key, label in PracticeExercise.Difficulty.choices],
    })


@never_cache
@api_view(['GET', 'POST'])
def exercise(request, slug):
    versions = PracticeVersion.objects.select_related('exercise', 'sign', 'plate_a', 'plate_b')
    preview = request.query_params.get('preview')
    if preview is not None:
        if request.method != 'GET' or not request.user.is_superuser or not preview.isascii() \
                or not preview.isdecimal() or len(preview) > 18:
            raise NotFound()
        version = get_object_or_404(versions, pk=preview, exercise__slug=slug)
        return Response(exercise_data(request, version, True))

    current = get_object_or_404(public_exercises().select_related(
        'published_version__sign', 'published_version__plate_a', 'published_version__plate_b',
    ), slug=slug)
    if request.method == 'GET':
        return Response(exercise_data(request, current.published_version, False))

    data = object_data(request)
    version_id = data.get('version')
    if type(version_id) is not int or not 1 <= version_id < 10**18:
        raise ValidationError({'detail': 'Откройте задание заново.'})
    version = get_object_or_404(
        public_versions(versions), pk=version_id, exercise=current,
        published_at__isnull=False, withdrawn_at__isnull=True,
    )
    try:
        correct = check_practice(version, data.get('answer'))
    except ModelValidationError as error:
        raise ValidationError({'detail': error.messages[0]}) from error
    if correct:
        if request.user.is_authenticated:
            PracticeResult.objects.get_or_create(user=request.user, version=version)
        else:
            completed = guest_completions(request)
            completed.pop(str(version.pk), None)
            completed[str(version.pk)] = timezone.now().timestamp()
            request.session[GUEST_RESULTS] = dict(list(completed.items())[-30:])
    return Response({
        'correct': correct, 'explanation': version.explanation, 'source_url': version.source_url,
        'sign': sign_link(version.sign), 'version': version.pk,
    })


@never_cache
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def practice_history(request):
    published = set(public_exercises().values_list('pk', flat=True))
    results = request.user.practice_results.select_related('version__exercise')[:50]
    return Response([
        {'id': result.pk, 'title': result.version.exercise.title, 'completed_at': result.completed_at,
         'version': result.version_id,
         'slug': result.version.exercise.slug if result.version.exercise_id in published else None}
        for result in results
    ])


@never_cache
@require_safe
def practice_photo(request, name):
    images = PracticeImage.objects.filter(image='practice/' + name)
    if not request.user.is_superuser:
        versions = PracticeVersion.objects.filter(
            exercise__in=public_exercises(), published_at__isnull=False, withdrawn_at__isnull=True,
        )
        images = images.filter(version__in=public_versions(versions))
    item = images.first()
    if not item:
        raise Http404
    return image_response(item.image)
