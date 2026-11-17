from random import Random
from secrets import token_hex

from .route_situations import MORE_SCENES


VERSION = 2
RULES = 'https://www.mos.ru/upload/content/files/66465faf978d133f00173e8fbe68c9fc/1090-PPRFot23101993_Opravilahdoroj_dvij%28sizmna16072025deistvs01092025po28022029%29.pdf'

SCENES = {
    'signal': (
        'У светофора',
        'На пешеходном светофоре горит красный. Перед тобой размеченный переход.',
        'ПДД, пункты 4.4 и 6.5',
        (
            ('wait', 'Дождаться зелёного, убедиться в безопасности и перейти', 'Красный запрещает движение. Переходи на разрешающий сигнал, убедившись, что путь свободен.'),
            ('cross', 'Перейти сейчас, пока машин мало', 'Красный сигнал запрещает переход, даже когда машин не видно.'),
        ),
    ),
    'zebra': (
        'Нерегулируемый переход',
        'На дороге размечена зебра. Слева приближается автомобиль. Светофора здесь нет.',
        'ПДД, пункт 4.5',
        (
            ('check', 'Оценить скорость машины и перейти, когда это безопасно', 'Перед выходом на зебру оцени расстояние, скорость машин и убедись, что переход безопасен.'),
            ('hurry', 'Выйти на дорогу сразу, потому что здесь зебра', 'Разметка обозначает переход. Перед выходом нужно проверить, что идти безопасно.'),
        ),
    ),
    'visibility': (
        'Переход рядом с автобусом',
        'У остановки стоит автобус и закрывает обзор дороги. Чуть дальше виден пешеходный переход с хорошим обзором.',
        'ПДД, пункты 4.3 и 4.5',
        (
            ('walk', 'Дойти до перехода с хорошим обзором и проверить дорогу', 'Используй видимый переход и оцени обстановку перед выходом на дорогу.'),
            ('bus', 'Выйти на дорогу из-за автобуса', 'За автобусом легко не заметить приближающийся транспорт. Дойди до перехода.'),
        ),
    ),
    'bikelane': (
        'Начало велодорожки',
        'Отсюда в сторону школы идёт отдельная велодорожка. Рядом проходят тротуар и дорога для машин.',
        'ПДД, пункт 24.1',
        (
            ('cycle', 'Поехать по велодорожке', 'В этой ситуации велосипедист старше 14 лет движется по велосипедной дорожке.'),
            ('traffic', 'Выехать на дорогу для машин', 'Рядом есть велодорожка. Используй её для движения в этом направлении.'),
        ),
    ),
    'dismount': (
        'Велодорожка заканчивается',
        'Дальше путь к школе проходит через пешеходный переход. Велопереезда на этом участке нет.',
        'ПДД, пункт 24.8',
        (
            ('dismount', 'Сойти с велосипеда и провести его через переход', 'Когда ведёшь велосипед рядом с собой, ты пешеход. Перед переходом проверь дорогу.'),
            ('ride', 'Проехать по пешеходному переходу на велосипеде', 'На велосипеде нельзя пересекать дорогу по пешеходному переходу. Спешься и веди его рядом.'),
        ),
    ),
}


SCENES.update(MORE_SCENES)
WALK_SCENES = ('sidewalk', 'visibility', 'underpass', 'island', 'ambulance', 'diagonal', 'shoulder')
BIKE_SCENES = ('bike_crowd', 'bike_signal', 'bike_yield', 'handlebar', 'passenger', 'cargo')
RULE_PAGES = {
    '4.1': 21, '4.3': 22, '4.4': 22, '4.5': 23, '4.6': 23, '4.7': 23,
    '6.5': 25, '24.1': 47, '24.6': 48, '24.6¹': 48, '24.8': 49,
}


def rule_url(rule):
    last_clause = rule.split()[-1]
    return f'{RULES}#page={RULE_PAGES[last_clause]}'


def point(label, x, y, *, text='', rule='', decision=False, kind='path', travel='walk'):
    return {
        'label': label, 'x': x, 'y': y, 'text': text, 'rule': rule,
        'decision': decision, 'kind': kind, 'travel': travel, 'choices': [],
    }


def choice(key, label, target, feedback=''):
    return {'id': key, 'label': label, 'target': target, 'feedback': feedback}


def legacy_scenes(level, random):
    if level == 'pedestrian':
        scenes = ['signal', random.choice(['visibility', 'zebra'])]
        random.shuffle(scenes)
        return scenes
    if level == 'detour':
        return [random.choice(['signal', 'visibility']), 'works', 'zebra']
    return ['bikelane', 'dismount', random.choice(['signal', 'zebra'])]


def new_scenes(level, random):
    if level == 'pedestrian':
        scenes = ['signal', 'zebra', *random.sample(WALK_SCENES, 4)]
        random.shuffle(scenes)
        return scenes
    if level == 'detour':
        scenes = ['signal', 'zebra', *random.sample(WALK_SCENES, 5)]
        random.shuffle(scenes)
        scenes.insert(3, 'works')
        return scenes
    bike = random.sample(BIKE_SCENES, 5)
    on_foot = random.sample(('signal', 'zebra', 'visibility', 'island'), 2)
    return ['bikelane', *bike, 'dismount', *on_foot]


def district(level, seed, version=VERSION):
    random = Random(seed)
    legacy = version == 1
    scenes = legacy_scenes(level, random) if legacy else new_scenes(level, random)
    start, finish = (9, 91) if legacy else (7, 93)
    travel = 'ride' if level == 'cycling' else 'walk'
    result = {
        'home': point('Дом', start, random.choice([38, 60]),
                      text='Выйди из дома и доберись до школы.', kind='home', travel=travel),
    }
    result['home']['choices'] = [choice('go', 'Начать путь', 'point-1')]
    edges = [('home', 'point-1')]
    for index, scene in enumerate(scenes, start=1):
        key = f'point-{index}'
        following = f'point-{index + 1}' if index < len(scenes) else 'school'
        x = start + round((finish - start) * index / (len(scenes) + 1))
        if scene == 'works':
            result[key] = point(
                'Ограждение', x, 51, decision=True,
                text='Дорожка прямо закрыта ограждением. Слева есть открытый проход через сквер, справа — открытая пешеходная дорожка. Обходы сходятся после ограждения.',
                rule='ПДД, пункт 4.1', kind='works',
            )
            result[key]['choices'] = [
                choice('park', 'Обойти через сквер', 'park', 'Проход через сквер открыт и отделён от машин.'),
                choice('walkway', 'Обойти по пешеходной дорожке', 'walkway', 'По открытой пешеходной дорожке можно обойти работы.'),
                choice('fence', 'Пройти за ограждение', None, 'Ограждение отмечает закрытый участок. Воспользуйся одним из открытых обходов.'),
            ]
            for branch, label, y in [('park', 'Сквер', 17), ('walkway', 'Дорожка', 84)]:
                offset = 10 if legacy else 4
                result[branch] = point(label, x + offset, y, text='Обход выводит на следующую улицу.', kind=branch)
                result[branch]['choices'] = [
                    choice('go', 'Идти дальше', following),
                    choice('back', 'Вернуться к развилке', key),
                ]
                edges.extend([(key, branch), (branch, following)])
        else:
            label, description, rule, options = SCENES[scene]
            y = random.choice([44, 57]) if level == 'detour' else random.choice([27, 47, 69])
            result[key] = point(label, x, y, text=description, rule=rule, decision=True, kind=scene, travel=travel)
            result[key]['choices'] = [
                choice(action, title, following if option == 0 else None, feedback)
                for option, (action, title, feedback) in enumerate(options)
            ]
            edges.append((key, following))
            if scene == 'dismount':
                travel = 'walk-bike'
        random.shuffle(result[key]['choices'])
    result['school'] = point('Школа', finish, random.choice([36, 62]), kind='school', travel=travel)
    return result, edges


def start_route(level):
    return {
        'id': token_hex(16), 'version': VERSION, 'level': level, 'seed': token_hex(8),
        'path': ['home'], 'solved': [], 'mistake_events': [], 'revision': 0, 'feedback': None,
        'last_choice': None,
    }


def restore_route(state):
    if not state or 'mistake_events' in state or state['version'] != 1:
        return state
    points, _ = district(state['level'], state['seed'], state['version'])
    return {
        **state,
        **({'original_score': len(state['solved'])} if state['path'][-1] == 'school' else {}),
        'mistake_events': [
            {'point': key, 'rule': points[key]['rule'], 'opened_at': None}
            for key in state['mistakes']
        ],
    }


def pending_rule(state):
    events = state['mistake_events']
    feedback = state['feedback']
    if events and feedback and not feedback['accepted'] and not events[-1]['opened_at']:
        return events[-1]['rule']
    return ''


def route_data(state):
    points, edges = district(state['level'], state['seed'], state['version'])
    current = state['path'][-1]
    scene = points[current]
    events = state['mistake_events']
    rule = pending_rule(state)
    solved = len(state['solved'])
    return {
        'id': state['id'], 'level': state['level'], 'revision': state['revision'], 'current': current,
        'points': [
            {'id': key, 'label': node['label'], 'x': node['x'], 'y': node['y']}
            for key, node in points.items()
        ],
        'edges': edges, 'path': state['path'],
        'scene': {key: scene[key] for key in ('label', 'text', 'kind', 'travel')},
        'choices': [] if rule else [{key: option[key] for key in ('id', 'label')} for option in scene['choices']],
        'feedback': state['feedback'], 'required_rule': rule, 'completed': current == 'school',
        'score': state.get('original_score', solved - len(events)),
        'total': sum(node['decision'] for node in points.values()),
        'solved': solved, 'mistakes': len(events), 'rules_opened': sum(bool(event['opened_at']) for event in events),
        'corrected': sum(event['point'] in state['solved'] for event in events),
        'ranked_version': state['version'] == VERSION,
    }


def apply_choice(state, option_id):
    points, _ = district(state['level'], state['seed'], state['version'])
    current = state['path'][-1]
    scene = points[current]
    option = next((option for option in scene['choices'] if option['id'] == option_id), None)
    if option is None:
        return False
    destination = option['target']
    if not destination:
        state['mistake_events'].append({'point': current, 'rule': scene['rule'], 'opened_at': None})
    elif scene['decision'] and current not in state['solved']:
        state['solved'].append(current)
    if destination:
        path = state['path']
        state['path'] = path[:path.index(destination) + 1] if destination in path else [*path, destination]
    state['feedback'] = {
        'accepted': destination is not None, 'text': option['feedback'], 'rule': scene['rule'],
        'url': rule_url(scene['rule']) if scene['rule'] else '',
    } if option['feedback'] else None
    state['revision'] += 1
    state['last_choice'] = option_id
    return True
