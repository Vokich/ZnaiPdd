from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import PracticeExercise, PracticeImage, PracticeVersion, RoadSign


SIGN_FIELDS = ('sign', 'plate_a', 'plate_b')


def public_versions(queryset):
    for field in SIGN_FIELDS:
        queryset = queryset.filter(Q(**{f'{field}__isnull': True}) | Q(**{f'{field}__is_published': True}))
    return queryset


def public_exercises():
    versions = public_versions(PracticeVersion.objects.filter(published_at__isnull=False, withdrawn_at__isnull=True))
    return PracticeExercise.objects.filter(published_version_id__in=versions.values('pk'))


def exercise_card(exercise):
    return {
        'slug': exercise.slug, 'title': exercise.title, 'topic': exercise.get_topic_display(),
        'difficulty': exercise.get_difficulty_display(), 'kind': exercise.published_version.get_kind_display(),
        'kind_id': exercise.published_version.kind,
    }


def related_exercises(sign):
    return public_exercises().filter(
        Q(published_version__sign=sign) | Q(published_version__plate_a=sign) | Q(published_version__plate_b=sign)
    )


def ints_in_range(values, size):
    return isinstance(values, list) and bool(values) and all(
        type(value) is int and 1 <= value <= size for value in values
    )


def validate_practice(version):
    data = version.content
    if version.kind == PracticeVersion.Kind.ORDER:
        cards = data.get('cards', [])
        orders = data.get('orders', [])
        if not 3 <= len(cards) <= 5 or len(set(cards)) != len(cards):
            raise ValidationError('Для порядка действий нужны 3–5 разных карточек.')
        if not orders or any(not ints_in_range(order, len(cards)) or sorted(order) != list(range(1, len(cards) + 1))
                             for order in orders):
            raise ValidationError('В каждом верном порядке перечислите все номера карточек по одному разу.')
    elif version.kind == PracticeVersion.Kind.PLATES:
        if not all(getattr(version, field + '_id') for field in SIGN_FIELDS) or version.plate_a_id == version.plate_b_id:
            raise ValidationError('Выберите знак и две разные таблички.')
        if version.sign.category == RoadSign.Category.DOP_INFO:
            raise ValidationError('В поле «Знак» выберите основной знак.')
        for key, answers in (('meanings', ('right_meanings',)), ('conditions', ('right_a', 'right_b'))):
            options = data.get(key, [])
            if len(options) < 2 or len(set(options)) != len(options):
                raise ValidationError('Для каждого фрагмента нужны как минимум два разных варианта.')
            if any(not ints_in_range(data.get(answer), len(options)) for answer in answers):
                raise ValidationError('Укажите верные номера фрагментов для знака и для обеих табличек.')
    else:
        raise ValidationError('Выберите формат задания.')


@transaction.atomic
def publish_practice(version_id):
    owner_id = PracticeVersion.objects.values_list('exercise_id', flat=True).get(pk=version_id)
    exercise = PracticeExercise.objects.select_for_update().get(pk=owner_id)
    version = PracticeVersion.objects.select_for_update().get(pk=version_id)
    if version.withdrawn_at:
        raise ValidationError('Создайте новую версию на основе отозванной.')
    if not version.published_at:
        version.full_clean()
        validate_practice(version)
        if version.kind == PracticeVersion.Kind.ORDER and (version.plate_a_id or version.plate_b_id):
            raise ValidationError('У задания на порядок действий можно указать знак. Таблички нужны для второго формата.')
        for field in SIGN_FIELDS:
            sign = getattr(version, field)
            if sign and (not sign.is_published or not sign.image_url):
                raise ValidationError('Для публикации выберите опубликованные знаки и таблички с изображениями.')
        version.published_at = timezone.now()
        version.save(update_fields=['published_at'])
    elif not public_versions(PracticeVersion.objects.filter(pk=version.pk)).exists():
        raise ValidationError('Сначала опубликуйте связанные знаки и таблички.')
    exercise.published_version = version
    exercise.save(update_fields=['published_version'])


@transaction.atomic
def withdraw_practice(version_id):
    owner_id = PracticeVersion.objects.values_list('exercise_id', flat=True).get(pk=version_id)
    exercise = PracticeExercise.objects.select_for_update().get(pk=owner_id)
    version = PracticeVersion.objects.select_for_update().get(pk=version_id)
    if version.published_at and not version.withdrawn_at:
        version.withdrawn_at = timezone.now()
        version.save(update_fields=['withdrawn_at'])
        if exercise.published_version_id == version.pk:
            exercise.published_version = None
            exercise.save(update_fields=['published_version'])


@transaction.atomic
def copy_practice_version(version):
    draft = PracticeVersion.objects.create(
        exercise=version.exercise, kind=version.kind, prompt=version.prompt,
        explanation=version.explanation, source_url=version.source_url, sign=version.sign,
        plate_a=version.plate_a, plate_b=version.plate_b, content=version.content,
    )
    PracticeImage.objects.bulk_create([
        PracticeImage(version=draft, image=item.image.name, alt=item.alt, caption=item.caption, order=item.order)
        for item in version.images.all()
    ])
    return draft


def check_practice(version, answer):
    data = version.content
    if version.kind == PracticeVersion.Kind.ORDER:
        if not ints_in_range(answer, len(data['cards'])) or sorted(answer) != list(range(1, len(data['cards']) + 1)):
            raise ValidationError('Расставьте все карточки по одному разу.')
        return answer in data['orders']
    if not isinstance(answer, list) or len(answer) != 3 or not ints_in_range(answer[:1], len(data['meanings'])) \
            or not ints_in_range(answer[1:], len(data['conditions'])):
        raise ValidationError('Выберите смысл знака и условие для обеих табличек.')
    meaning, first, second = answer
    return meaning in data['right_meanings'] and first in data['right_a'] and second in data['right_b']
