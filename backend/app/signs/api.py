from random import shuffle

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.common.http import object_data
from app.models import RoadSign
from app.practice.service import related_exercises
from app.reporting.records import save_sign_answer
from app.signs.catalog import catalog_signs, learned_sign_ids, published_signs


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


@never_cache
@api_view(['GET'])
def signs(request):
    unlocked_ids = learned_sign_ids(request.user)
    signs = catalog_signs(request.query_params.get('category', ''), request.query_params.get('q', ''),
                         learned=unlocked_ids if request.query_params.get('learned') == '1' else None)
    page = Paginator(signs, 24).get_page(request.query_params.get('page', 1))
    return Response({
        'categories': [{'value': value, 'label': label} for value, label in RoadSign.Category.choices],
        'total': published_signs().count(),
        'unlocked_count': len(unlocked_ids),
        'signs': [sign_data(sign, sign.pk in unlocked_ids) for sign in page],
        'page': page.number, 'pages': page.paginator.num_pages,
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
    if not save_sign_answer(request.user, sign, answer):
        raise ValidationError({'answer': ['Неверный ответ. Попробуйте ещё раз.']})
    return Response({'unlocked': True})
