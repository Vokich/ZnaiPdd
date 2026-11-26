from django.db.models import F, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce, Concat

from app.routes.engine import STARTER_SCENES


LEVELS = {
    key: {'title': STARTER_SCENES['level-' + key]['title'], 'description': STARTER_SCENES['level-' + key]['prompt'],
          'total': total}
    for key, total in (('pedestrian', 6), ('detour', 8), ('cycling', 9))
}


def published_levels():
    from app.models import RouteSceneContent
    rows = {row.key[6:]: row for row in RouteSceneContent.objects.filter(key__startswith='level-')}
    return {key: {**level, 'title': rows[key].title, 'description': rows[key].prompt} for key, level in LEVELS.items()}


def with_route_title(queryset, field):
    from app.models import RouteSceneContent

    titles = RouteSceneContent.objects.filter(key=Concat(Value('level-'), OuterRef(field))).values('title')
    return queryset.annotate(route_title=Coalesce(Subquery(titles[:1]), F(field)))
