from django.http import Http404
from django.db import connection
from django.db.models import Value, CharField
from django.db.models.functions import Concat, Lower, Replace
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from app.editorial.media import image_response
from app.models import RoadSign, UserSignProgress


def published_signs():
    return RoadSign.objects.filter(is_published=True)


def catalog_signs(category='', query='', learned=None):
    signs = published_signs()
    if learned is not None:
        signs = signs.filter(pk__in=learned)
    if category:
        signs = signs.filter(category=category)
    term = query[:120].strip().removeprefix('№').strip().casefold().replace('ё', 'е')
    if not term:
        return signs
    if connection.vendor == 'postgresql':
        name = Replace(Lower(Concat('number', Value(' '), 'name', output_field=CharField())), Value('ё'), Value('е'))
        return signs.alias(searchable=name).filter(searchable__contains=term)
    return [sign for sign in signs if term in f'{sign.number} {sign.name}'.casefold().replace('ё', 'е')]


def learned_sign_ids(user):
    if not user.is_authenticated:
        return set()
    return set(user.sign_progress.filter(unlocked=True, sign__is_published=True).values_list('sign_id', flat=True))


def mark_sign_learned(user, sign):
    progress, _ = UserSignProgress.objects.get_or_create(user=user, sign=sign)
    UserSignProgress.objects.filter(pk=progress.pk, unlocked=False).update(
        unlocked=True, test_passed_at=timezone.now(),
    )


@never_cache
@require_safe
def uploaded_sign_image(request, name):
    path = 'signs/' + name
    matching = RoadSign.objects.filter(image=path)
    if not (request.user.is_staff and request.user.has_perm('app.view_roadsign')):
        matching = matching.filter(is_published=True)
    sign = matching.first()
    if not sign:
        raise Http404
    return image_response(sign.image)
