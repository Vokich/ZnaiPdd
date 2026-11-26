from django.core.paginator import Paginator
from django.db.models import Count, F, Sum
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.common.http import object_data
from app.models import Profile
from app.routes.levels import published_levels
from app.rankings.scores import SECTIONS, scored_profiles


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
    teams = request.query_params.get('view') == 'organizations'
    section = request.query_params.get('section', 'all')
    if section not in SECTIONS:
        raise ValidationError({'detail': 'Выберите направление рейтинга.'})
    own = scored_profiles(Profile.objects.filter(user=request.user), section)
    own_points = own.values_list('points', flat=True).first()
    profiles = Profile.objects.filter(competition_enabled=True, user__is_active=True).exclude(surname1='').exclude(name='')
    if teams:
        profiles = profiles.filter(organization_confirmed=True, organization__isnull=False)
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

    profiles = scored_profiles(profiles, section)
    if teams:
        profiles = (profiles.values('organization_id', 'organization__name', 'organization__municipality__name')
                    .annotate(points=Sum(F('points')), members=Count('pk'))
                    .order_by('-points', 'organization__name', 'organization_id'))
    else:
        profiles = profiles.select_related('organization').order_by('-points', 'pk')
    paginator = Paginator(profiles, 25)
    page = paginator.get_page(request.query_params.get('page', 1))
    rows = list(page.object_list)
    entries = []

    def points(row):
        return row['points'] if teams else row.points

    place = profiles.filter(points__gt=points(rows[0])).count() + 1 if rows else 0
    previous_points = points(rows[0]) if rows else None
    for index, row in enumerate(rows, start=page.start_index()):
        if points(row) != previous_points:
            place = index
            previous_points = points(row)
        if teams:
            entries.append(dict(place=place, name=row['organization__name'], points=points(row),
                                municipality=row['organization__municipality__name'], members=row['members']))
        else:
            entries.append({
                'place': place, 'name': ' '.join(filter(None, (row.surname1, row.name, row.surname2))),
                'organization': row.organization.name if row.organization else None,
                'points': row.points, 'is_current_user': row.user_id == request.user.pk,
            })
    municipalities = {row['organization__municipality_id']: row['organization__municipality__name']
                      for row in organizations}
    sections = {**SECTIONS, **{'route-' + key: level['title'] for key, level in published_levels().items()}}
    return Response({
        'entries': entries, 'page': page.number, 'pages': paginator.num_pages, 'maximum': None,
        'my_points': own_points,
        'sections': [{'id': key, 'name': label} for key, label in sections.items()],
        'organizations': [
            {'id': row['organization_id'], 'name': row['organization__name'],
             'municipality': row['organization__municipality__name']}
            for row in organizations
        ],
        'municipalities': [
            {'id': key, 'name': name} for key, name in sorted(municipalities.items(), key=lambda item: item[1])
        ],
    })
