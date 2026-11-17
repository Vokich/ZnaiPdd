from django.db.models import Count, F, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce, Greatest, Least, NullIf

from .models import PracticeResult, PracticeVersion, Profile, RouteResult, TestResult
from .practice import public_exercises, public_versions
from .route_levels import LEVELS


ROUTE_SECTIONS = {f'route-{key}': level['title'] for key, level in LEVELS.items()}
TEST_SECTIONS = {f'test-{key}': label for key, label in TestResult.TestType.choices}
SECTIONS = {
    'all': 'Общий зачёт',
    'routes': 'Безопасные маршруты',
    **ROUTE_SECTIONS,
    'tests': 'Возрастные тесты',
    **TEST_SECTIONS,
    'practice': 'Практика ПДД',
}


def best_route(level):
    results = RouteResult.objects.filter(user_id=OuterRef('user_id'), level=level).order_by('-score')
    return Subquery(results.values('score')[:1], output_field=IntegerField())


def best_test(test_type=None):
    results = TestResult.objects.filter(user_id=OuterRef('user_id'), total_questions__gt=0)
    if test_type:
        results = results.filter(test_type=test_type)
    results = results.annotate(percent=Least(100, Greatest(0, F('score') * 100 / NullIf(F('total_questions'), 0))))
    return Subquery(results.order_by('-percent').values('percent')[:1], output_field=IntegerField())


def practice_rating():
    exercises = public_exercises()
    total = exercises.count()
    if not total:
        return Value(None, output_field=IntegerField()), 0
    versions = public_versions(PracticeVersion.objects.filter(
        exercise__in=exercises, published_at__isnull=False, withdrawn_at__isnull=True,
    ))
    completed = PracticeResult.objects.filter(user_id=OuterRef('user_id'), version__in=versions)
    completed = completed.order_by().values('user_id').annotate(count=Count('version__exercise', distinct=True))
    return Subquery(completed.values('count')[:1], output_field=IntegerField()) * 100 / total, 100


def route_scores(profiles):
    profiles = profiles.alias(**{key: best_route(key) for key in LEVELS})
    route_attempts = Q()
    route_points = Value(0)
    for level in LEVELS:
        route_attempts |= Q(**{f'{level}__isnull': False})
        route_points += Greatest(0, Coalesce(F(level), 0))
    route_max = sum(level['total'] for level in LEVELS.values())
    return profiles.alias(route_points=route_points * 100 / route_max), route_attempts


def rating_overview(user_id):
    profiles, _ = route_scores(Profile.objects.filter(user_id=user_id))
    practice_points, practice_max = practice_rating()
    fields = ['route_points', 'test_points']
    if practice_max:
        fields.append('practice_points')
    row = profiles.annotate(
        route_points=F('route_points'), test_points=Coalesce(best_test(), 0),
        practice_points=Coalesce(practice_points, 0),
    ).values(*fields).first() or {}
    routes = row.get('route_points', 0)
    tests = row.get('test_points', 0)
    practice = row.get('practice_points', 0)
    directions = [
        {'id': 'routes', 'points': routes},
        {'id': 'tests', 'points': tests},
    ]
    if practice_max:
        directions.append({'id': 'practice', 'points': practice})
    return {'points': routes + tests + practice, 'maximum': 200 + practice_max, 'directions': directions}


def scored_profiles(profiles, section):
    if section == 'practice':
        practice_points, _ = practice_rating()
        return profiles.annotate(points=practice_points).filter(points__isnull=False), 100
    if section in ROUTE_SECTIONS:
        level = section.removeprefix('route-')
        total = LEVELS[level]['total']
        profiles = profiles.alias(best=best_route(level)).filter(best__isnull=False)
        return profiles.annotate(points=Greatest(0, F('best'))), total
    if section in TEST_SECTIONS:
        profiles = profiles.annotate(points=best_test(section.removeprefix('test-')))
        return profiles.filter(points__isnull=False), 100

    if section in ('all', 'routes'):
        profiles, route_attempts = route_scores(profiles)
        if section == 'routes':
            return profiles.filter(route_attempts).annotate(points=F('route_points')), 100
        practice_points, practice_max = practice_rating()
        profiles = profiles.alias(test_points=best_test(), practice_points=practice_points)
        profiles = profiles.filter(route_attempts | Q(test_points__isnull=False) | Q(practice_points__isnull=False))
        points = F('route_points') + Coalesce(F('test_points'), 0) + Coalesce(F('practice_points'), 0)
        return profiles.annotate(points=points), 200 + practice_max

    profiles = profiles.annotate(points=best_test())
    return profiles.filter(points__isnull=False), 100
