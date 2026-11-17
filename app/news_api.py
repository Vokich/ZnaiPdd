from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .media import gallery_data, image_response
from .models import NewsImage, NewsPost
from .practice import public_exercises
from .practice_api import exercise_card, sign_link


def published_posts(now):
    return NewsPost.objects.filter(published_at__lte=now)


def upcoming_posts(now):
    return published_posts(now).filter(
        kind=NewsPost.Kind.EVENT, cancelled=False, starts_at__gt=now,
    ).order_by('starts_at', 'id')


def post_card(post, now):
    event = None
    if post.kind == NewsPost.Kind.EVENT:
        event = {
            'starts_at': post.starts_at, 'timezone': post.timezone_name,
            'timezone_label': post.get_timezone_name_display(),
            'venue': post.venue, 'audience': post.audience, 'organizer': post.organizer,
            'cancelled': post.cancelled, 'past': post.starts_at <= now if post.starts_at else False,
            'registration_deadline': post.registration_deadline,
        }
    return {
        'title': post.title, 'slug': post.slug, 'summary': post.summary,
        'cover': post.cover.url if post.cover else None, 'cover_credit': post.cover_credit,
        'published_at': post.published_at, 'kind': post.kind,
        'kind_label': post.get_kind_display(), 'event': event,
    }


@never_cache
@api_view(['GET'])
def news_feed(request):
    now = timezone.now()
    tab = request.query_params.get('tab')
    posts = published_posts(now)
    if tab == 'upcoming':
        posts = upcoming_posts(now)
    elif tab == 'archive':
        posts = posts.filter(Q(kind=NewsPost.Kind.EVENT) & (Q(cancelled=True) | Q(starts_at__lte=now)))
    page = Paginator(posts, 12).get_page(request.query_params.get('page'))
    return Response({'items': [post_card(post, now) for post in page], 'page': page.number, 'pages': page.paginator.num_pages})


@never_cache
@api_view(['GET'])
def next_event(request):
    now = timezone.now()
    event = upcoming_posts(now).first()
    return Response({'event': post_card(event, now) if event else None})


@never_cache
@api_view(['GET'])
def news_post(request, slug):
    now = timezone.now()
    post = get_object_or_404(published_posts(now), slug=slug)
    data = post_card(post, now)
    event = data['event']
    registration_open = (
        event and not (event['cancelled'] or event['past'])
        and (not post.registration_deadline or post.registration_deadline > now)
    )
    data.update({
        'body': post.body,
        'images': gallery_data(post.images.all()),
        'registration_url': post.registration_url if registration_open else '',
        'signs': [sign_link(sign) for sign in post.signs.filter(is_published=True)],
        'exercises': [exercise_card(exercise) for exercise in public_exercises().select_related('published_version')
                      .filter(pk__in=post.exercises.values('pk'))],
    })
    return Response(data)


@never_cache
@require_safe
def news_cover(request, name):
    posts = NewsPost.objects.all() if request.user.is_superuser else published_posts(timezone.now())
    post = get_object_or_404(posts, cover='news/' + name)
    return image_response(post.cover)


@never_cache
@require_safe
def news_photo(request, name):
    images = NewsImage.objects.all()
    if not request.user.is_superuser:
        images = images.filter(post__published_at__lte=timezone.now())
    item = get_object_or_404(images, image='news/gallery/' + name)
    return image_response(item.image)
