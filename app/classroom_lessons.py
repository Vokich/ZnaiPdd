from django.core.exceptions import ValidationError as ModelValidationError
from django.templatetags.static import static
from rest_framework.exceptions import ValidationError

from .models import PracticeVersion
from .practice import check_practice
from .safe_routes import SCENES, rule_url, scene_choices
from .starter_practice import ORDER_LESSONS
from .starter_road_signs import RULEBOOK, STARTER_SIGNS


LESSONS = {
    'road-crossing': {
        'title': 'Переход дороги', 'audience': 'Младшие школьники', 'minutes': 10,
        'sign': '1.22', 'exercise': 'zebra-check', 'scene': 'visibility',
    },
    'bike-crossing': {
        'title': 'Велосипед на переходе', 'audience': 'Школьники 12–16 лет', 'minutes': 15,
        'sign': '4.4.1', 'exercise': 'walk-the-bike', 'scene': 'dismount',
    },
}


def run_title(run):
    return run.version.title if run.version_id else LESSONS[run.lesson]['title']


def lesson_steps(key):
    lesson = LESSONS[key]
    sign = next(row for row in STARTER_SIGNS if row[0] == lesson['sign'])
    exercise = next(row for row in ORDER_LESSONS if row[0] == lesson['exercise'])
    title, prompt, rule, choices = SCENES[lesson['scene']]
    return [
        {'title': sign[1], 'prompt': sign[5], 'image': static(f'road-signs/{sign[0]}.png'),
         'explanation': sign[4], 'source': f'{RULEBOOK}#page={sign[3]}'},
        {'title': exercise[1], 'prompt': exercise[6],
         'cards': [{'id': i, 'text': exercise[8][i - 1]} for i in range(len(exercise[8]), 0, -1)],
         'explanation': exercise[7], 'source': f'{RULEBOOK}#page={exercise[5]}',
         'orders': exercise[9]},
        {'title': title, 'prompt': prompt, 'choices': [{'id': i, 'text': label} for i, label, _ in reversed(choices)],
         'explanation': choices[0][2], 'source': rule_url(rule)},
    ]


def lesson_card(key):
    lesson = LESSONS[key]
    return {'id': key, **{field: lesson[field] for field in ('title', 'audience', 'minutes')},
            'plan': [step['title'] for step in lesson_steps(key)]}


def presentation(key):
    return [{k: v for k, v in step.items() if k not in ('explanation', 'orders', 'source')}
            for step in lesson_steps(key)]


def explain(key, step_id, answer):
    if type(step_id) is not int or step_id not in range(3):
        raise ValidationError({'detail': 'Выберите шаг урока.'})
    step = lesson_steps(key)[step_id]
    correct = None
    explanation = step['explanation']
    if answer is not None and step_id == 1:
        version = PracticeVersion(kind='order', content={'cards': step['cards'], 'orders': step['orders']})
        try:
            correct = check_practice(version, answer)
        except ModelValidationError as exc:
            raise ValidationError({'detail': exc.messages[0]}) from exc
    if answer is not None and step_id == 2:
        choices = scene_choices(LESSONS[key]['scene'], 'school')
        choice = next((row for row in choices if row['id'] == answer), None)
        if not choice:
            raise ValidationError({'detail': 'Выберите действие.'})
        correct = choice['target'] is not None
        explanation = choice['feedback']
    return {'correct': correct, 'explanation': explanation, 'source': step['source']}
