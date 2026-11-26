import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path


DIRECTORY_PATH = Path(__file__).resolve().parents[1] / 'data' / 'municipalities.json'


def search_words(value):
    words = re.findall(r'[^\W_]+', value.casefold().replace('ё', 'е'))
    return tuple('область' if word == 'обл' else word for word in words)


@lru_cache(maxsize=1)
def municipality_index():
    data = json.loads(DIRECTORY_PATH.read_text(encoding='utf-8'))
    entries = []
    for row in data['municipalities']:
        label = ', '.join(filter(None, (row['name'], row.get('district'), row['region'])))
        entries.append((label, row))

    counts = Counter(label for label, _ in entries)
    index = []
    regions = set()
    for label, row in entries:
        if counts[label] > 1:
            label = f"{label} ({row['code']})"
        region = tuple(sorted(search_words(row['region'])))
        regions.add(region)
        index.append((label, region, search_words(row['name']), search_words(label) + (row['code'],), row['code']))

    index.sort(key=lambda entry: entry[0].casefold().replace('ё', 'е'))
    return index, regions, {label: code for label, _, _, _, code in index}


def municipality_codes():
    return municipality_index()[2]


def search_municipalities(query):
    if len(query) > 400:
        return [], False
    words = search_words(query)
    if sum(map(len, words)) < 2:
        return [], False

    index, regions, _ = municipality_index()
    region = tuple(sorted(words))
    if region in regions:
        return [label for label, key, _, _, _ in index if key == region], False

    name_matches = []
    other_matches = []
    for label, _, name, terms, _ in index:
        if all(any(term.startswith(word) for term in name) for word in words):
            name_matches.append(label)
        elif all(any(term.startswith(word) for term in terms) for word in words):
            other_matches.append(label)

    matches = name_matches + other_matches
    return matches[:50], len(matches) > 50
