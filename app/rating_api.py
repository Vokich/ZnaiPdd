from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .api import object_data
from .models import Profile
from .rating import SECTIONS, scored_profiles


@never_cache
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def competition(request):
    enabled = object_data(request).get('enabled')
    if type(enabled) is not bool:
        raise ValidationError({'detail': 'Выберите режим участия.'})
    profile = getattr(request.user, 'profile', None)
    if not profile or (enabled and not (profile.surname1.strip() and profile.name.strip())):
        raise ValidationError({'detail': 'Укажите фамилию и имя в профиле.'})
    Profile.objects.filter(pk=profile.pk).update(competition_enabled=enabled)
    return Response({'enabled': enabled})


@never_cache
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rating(request):
    section = request.query_params.get('section', 'all')
    if section not in SECTIONS:
        raise ValidationError({'detail': 'Выберите направление рейтинга.'})
    own, _ = scored_profiles(Profile.objects.filter(user=request.user), section)
    own_points = own.values_list('points', flat=True).first()
    profiles = Profile.objects.filter(competition_enabled=True, user__is_active=True).exclude(surname1='').exclude(name='')
    organizations = list(
        profiles.filter(organization__isnull=False)
        .order_by('organization__name', 'organization__municipality__name', 'organization_id')
        .values(
            'organization_id', 'organization__name', 'organization__municipality__name',
            'organization__municipality_id',
        )
        .distinct()
    )
    organization = request.query_params.get('organization', '')
    municipality = request.query_params.get('municipality', '')
    if organization == 'none':
        profiles = profiles.filter(organization__isnull=True)
    elif organization:
        if not organization.isascii() or not organization.isdecimal() or len(organization) > 18:
            raise ValidationError({'detail': 'Выберите организацию из списка.'})
        profiles = profiles.filter(organization_id=organization)
    if municipality:
        profiles = profiles.filter(organization__municipality_id=municipality)

    profiles, maximum = scored_profiles(profiles, section)
    profiles = profiles.select_related('organization').order_by('-points', 'pk')
    paginator = Paginator(profiles, 25)
    page = paginator.get_page(request.query_params.get('page', 1))
    rows = list(page.object_list)
    entries = []
    place = profiles.filter(points__gt=rows[0].points).count() + 1 if rows else 0
    previous_points = rows[0].points if rows else None
    for index, profile in enumerate(rows, start=page.start_index()):
        if profile.points != previous_points:
            place = index
            previous_points = profile.points
        entries.append({
            'place': place, 'name': ' '.join(filter(None, (profile.surname1, profile.name, profile.surname2))),
            'organization': profile.organization.name if profile.organization else None,
            'points': profile.points, 'is_current_user': profile.user_id == request.user.pk,
        })
    municipalities = {row['organization__municipality_id']: row['organization__municipality__name']
                      for row in organizations}
    return Response({
        'entries': entries, 'page': page.number, 'pages': paginator.num_pages, 'maximum': maximum,
        'my_points': own_points,
        'sections': [{'id': key, 'name': label} for key, label in SECTIONS.items()],
        'organizations': [
            {'id': row['organization_id'], 'name': row['organization__name'],
             'municipality': row['organization__municipality__name']}
            for row in organizations
        ],
        'municipalities': [
            {'id': key, 'name': name} for key, name in sorted(municipalities.items(), key=lambda item: item[1])
        ],
    })
