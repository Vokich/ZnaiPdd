from django.db.models import Count, F, IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, Greatest, Least

from app.models import PlatformAttempt, PracticeResult, PracticeVersion, Profile, RouteResult, TestResult, UserSignProgress
from app.practice.service import public_exercises, public_versions
from app.routes.levels import LEVELS


ROUTE_SECTIONS = {f'route-{key}': level['title'] for key, level in LEVELS.items()}
TEST_SECTIONS = {f'test-{key}': label for key, label in TestResult.TestType.choices}
SECTIONS = {
    'all': 'Общий зачёт',
    'routes': 'Безопасные маршруты',
    **ROUTE_SECTIONS,
    'tests': 'Возрастные тесты',
    **TEST_SECTIONS,
    'practice': 'Практика ПДД',
    'signs': 'Мини-тесты по знакам',
    'qr': 'QR-тесты платформы',
}


def best_route(level):
    results = RouteResult.objects.filter(user_id=OuterRef('user_id'), level=level).order_by('-score')
    return Subquery(results.values('score')[:1], output_field=IntegerField())


def best_test(test_type):
    results = TestResult.objects.filter(user_id=OuterRef('user_id'), test_type=test_type, total_questions__gt=0)
    results = results.annotate(credit=Least(F('total_questions'), Greatest(0, F('score'))))
    return Subquery(results.order_by('-credit').values('credit')[:1], output_field=IntegerField())


def subtotal(rows, expression):
    grouped = rows.order_by().values('user_id').annotate(credit=expression)
    return Subquery(grouped.values('credit')[:1], output_field=IntegerField())


def task_credit(section):
    if section == 'practice':
        versions = public_versions(PracticeVersion.objects.filter(
            exercise__in=public_exercises(), published_at__isnull=False, withdrawn_at__isnull=True))
        results = PracticeResult.objects.filter(user_id=OuterRef('user_id'), version__in=versions)
        # Count distinct exercises even if the pupil passed several editions.
        basic = Count('version__exercise', distinct=True, filter=Q(version__exercise__difficulty='basic'))
        advanced = Count('version__exercise', distinct=True, filter=Q(version__exercise__difficulty='advanced'))
        return subtotal(results, basic * 3 + advanced * 5)
    if section == 'signs':
        rows = UserSignProgress.objects.filter(user_id=OuterRef('user_id'), unlocked=True, sign__is_published=True)
        return subtotal(rows, Count('pk'))
    if section == 'qr':
        best = PlatformAttempt.objects.filter(kind='qr', user_id=OuterRef('user_id'), task=OuterRef('task'))
        rows = PlatformAttempt.objects.filter(kind='qr', user_id=OuterRef('user_id'),
                                              pk=Subquery(best.order_by('-score', 'pk').values('pk')[:1]))
        return subtotal(rows, Sum('score'))
    if section in TEST_SECTIONS:
        return best_test(section.removeprefix('test-'))
    if section in ROUTE_SECTIONS:
        return best_route(section.removeprefix('route-'))


def category_tasks(section):
    if section == 'routes':
        return list(ROUTE_SECTIONS)
    if section == 'tests':
        return list(TEST_SECTIONS)
    if section == 'all':
        return [*ROUTE_SECTIONS, *TEST_SECTIONS, 'practice', 'qr', 'signs']
    return [section]


def scored_profiles(profiles, section):
    names = category_tasks(section)
    if len(names) == 1:
        scored = profiles.annotate(points=task_credit(names[0]))
    else:
        attempts = Q()
        expression = Value(0)
        for index, name in enumerate(names):
            key = f'credit_{index}'
            profiles = profiles.alias(**{key: task_credit(name)})
            attempts |= Q(**{key + '__isnull': False})
            expression += Greatest(0, Coalesce(F(key), 0))
        return profiles.filter(attempts).annotate(points=expression)
    return scored.filter(points__isnull=False)


def rating_overview(user_id):
    parts = ('routes', 'tests', 'practice', 'signs', 'qr')
    credits = {name: task_credit(name) for name in category_tasks('all')}
    row = Profile.objects.filter(user_id=user_id).annotate(**credits).values(*credits).first() or {}
    directions = [dict(id=key, points=sum(max(0, row.get(name) or 0) for name in category_tasks(key)))
                  for key in parts]
    return dict(points=sum(item['points'] for item in directions), maximum=None, directions=directions)
