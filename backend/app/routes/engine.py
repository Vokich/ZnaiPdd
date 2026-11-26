from random import Random
from secrets import token_hex

import json
from pathlib import Path


VERSION = 2
STARTER_SCENES = json.loads((Path(__file__).resolve().parents[1] / 'data' / 'route_scenes.json').read_text(encoding='utf-8'))


def route_content():
    from app.models import RouteSceneContent
    return {row['key']: row for row in RouteSceneContent.objects.values()}


def pool_keys(content, pool):
    # Keep seeded order so saved routes created before snapshots remain reproducible.
    keys = [key for key in STARTER_SCENES if key in content and content[key].get('pool') == pool]
    return keys + sorted(key for key in content.keys() - STARTER_SCENES.keys() if content[key].get('pool') == pool)


def rule_url(rule):
    return next((item['url'] for item in STARTER_SCENES.values() if item['rule'] == rule), '')


def point(label, x, y, *, text='', rule='', decision=False, kind='path', travel='walk'):
    return {
        'label': label, 'x': x, 'y': y, 'text': text, 'rule': rule,
        'decision': decision, 'kind': kind, 'travel': travel, 'choices': [],
    }


def choice(key, label, target, feedback=''):
    return {'id': key, 'label': label, 'target': target, 'feedback': feedback}


def scene_choices(item, destinations):
    return [choice(row['id'], row['label'], destinations.get(row['id']) if row['safe'] else None, row['feedback'])
            for row in item['choices']]


def legacy_scenes(level, random):
    if level == 'pedestrian':
        scenes = ['signal', random.choice(['visibility', 'zebra'])]
        random.shuffle(scenes)
        return scenes
    if level == 'detour':
        return [random.choice(['signal', 'visibility']), 'works', 'zebra']
    return ['bikelane', 'dismount', random.choice(['signal', 'zebra'])]


def new_scenes(level, random, content):
    if level == 'pedestrian':
        scenes = ['signal', 'zebra', *random.sample(pool_keys(content, 'walk'), 4)]
        random.shuffle(scenes)
        return scenes
    if level == 'detour':
        scenes = ['signal', 'zebra', *random.sample(pool_keys(content, 'walk'), 5)]
        random.shuffle(scenes)
        scenes.insert(3, 'works')
        return scenes
    bike = random.sample(pool_keys(content, 'bike'), 5)
    on_foot = random.sample(('signal', 'zebra', 'visibility', 'island'), 2)
    return ['bikelane', *bike, 'dismount', *on_foot]


def district(level, seed, version=VERSION, content=None):
    content = content or STARTER_SCENES
    random = Random(seed)
    legacy = version == 1
    scenes = legacy_scenes(level, random) if legacy else new_scenes(level, random, content)
    start, finish = (9, 91) if legacy else (7, 93)
    travel = 'ride' if level == 'cycling' else 'walk'
    def make_node(kind, x, y, destinations, decision=False):
        item = content[kind]
        node = point(item['title'], x, y, text=item['prompt'], rule=item['rule'], kind=kind,
                     travel=travel, decision=decision)
        node['url'] = item['url']
        node['choices'] = scene_choices(item, destinations)
        return node

    result = {'home': make_node('home', start, random.choice([38, 60]), {'go': 'point-1'})}
    edges = [('home', 'point-1')]
    for index, scene in enumerate(scenes, start=1):
        key = f'point-{index}'
        following = f'point-{index + 1}' if index < len(scenes) else 'school'
        x = start + round((finish - start) * index / (len(scenes) + 1))
        if scene == 'works':
            result[key] = make_node(scene, x, 51, {'park': 'park', 'walkway': 'walkway'}, True)
            for branch, y in [('park', 17), ('walkway', 84)]:
                offset = 10 if legacy else 4
                result[branch] = make_node(branch, x + offset, y, {'go': following, 'back': key})
                edges.extend([(key, branch), (branch, following)])
        else:
            y = random.choice([44, 57]) if level == 'detour' else random.choice([27, 47, 69])
            destinations = {row['id']: following for row in content[scene]['choices']}
            result[key] = make_node(scene, x, y, destinations, True)
            edges.append((key, following))
            if scene == 'dismount':
                travel = 'walk-bike'
        random.shuffle(result[key]['choices'])
    result['school'] = make_node('school', finish, random.choice([36, 62]), {})
    return result, edges


def start_route(level):
    seed = token_hex(8)
    content = route_content()
    nodes, edges = district(level, seed, content=content)
    return {
        'district': [list(nodes.items()), edges], 'responses': [],
        'title': content['level-' + level]['title'],
        'id': token_hex(16), 'version': VERSION, 'level': level, 'seed': seed,
        'path': ['home'], 'solved': [], 'mistake_events': [], 'revision': 0, 'feedback': None,
        'last_choice': None,
    }


def saved_district(state):
    if 'district' in state:
        nodes, edges = state['district']
        return dict(nodes), edges
    return district(state['level'], state['seed'], state['version'])


def restore_route(state):
    if not state or 'mistake_events' in state or state['version'] != 1:
        return state
    points, _ = saved_district(state)
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
    points, edges = saved_district(state)
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
    points, _ = saved_district(state)
    current = state['path'][-1]
    scene = points[current]
    option = next((option for option in scene['choices'] if option['id'] == option_id), None)
    if option is None:
        return False
    destination = option['target']
    if scene['decision']:
        state.setdefault('responses', []).append({
            'question': scene['text'], 'selected': option['label'],
            'expected': ' / '.join(sorted(row['label'] for row in scene['choices'] if row['target'])),
            'correct': bool(destination),
        })
    if not destination:
        state['mistake_events'].append({'point': current, 'rule': scene['rule'], 'url': scene['url'], 'opened_at': None})
    elif scene['decision'] and current not in state['solved']:
        state['solved'].append(current)
    if destination:
        path = state['path']
        state['path'] = path[:path.index(destination) + 1] if destination in path else [*path, destination]
    state['feedback'] = {
        'accepted': destination is not None, 'text': option['feedback'], 'rule': scene['rule'],
        'url': scene['url'],
    } if option['feedback'] else None
    state['revision'] += 1
    state['last_choice'] = option_id
    return True
