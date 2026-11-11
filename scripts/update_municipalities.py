import argparse
import csv
import io
import json
from pathlib import Path
from urllib.request import urlopen


OKTMO_URL = 'https://classifikators.ru/assets/downloads/oktmo/oktmo.csv'
REGIONS_URL = 'https://raw.githubusercontent.com/hflabs/region/master/region.csv'
OUTPUT_PATH = Path(__file__).resolve().parents[1] / 'app' / 'data' / 'municipalities.json'


def read_source(source):
    if source.startswith('https://'):
        with urlopen(source, timeout=45) as response:
            return response.read().decode('utf-8-sig')
    return Path(source).read_text(encoding='utf-8-sig')


def region_names(content):
    names = {
        '21000000': 'Донецкая Народная Республика',
        '23000000': 'Запорожская область',
        '43000000': 'Луганская Народная Республика',
        '74000000': 'Херсонская область',
    }
    for row in csv.DictReader(io.StringIO(content)):
        code, name, kind = row['oktmo'], row['name'], row['type']
        if kind == 'Респ':
            name = f'Республика {name}'
        elif kind == 'обл':
            name = 'Кемеровская область — Кузбасс' if name == 'Кемеровская' else f'{name} область'
        elif kind == 'край':
            name = f'{name} край'
        elif kind == 'АО' and 'округ' not in name:
            name = f'{name} автономный округ'
        elif kind == 'Аобл':
            name = f'{name} автономная область'
        if code:
            names[code] = name
    return names


def extract_municipalities(content, regions):
    names = {}
    for number, row in enumerate(csv.reader(io.StringIO(content), delimiter=';', strict=True), start=1):
        if not row or (number == 1 and row[0].casefold() == 'ter'):
            continue
        if len(row) != 13 or any(len(value) != size or not value.isascii() or not value.isdigit()
                                 for value, size in zip(row[:4], (2, 3, 3, 3))):
            raise ValueError(f'Неожиданный формат ОКТМО в строке {number}')
        region, district, settlement, locality, _, section, name = row[:7]

        # В первом разделе 00 в конце кода уровня обозначает группировку, а не муниципалитет.
        if section != '1' or locality != '000' or district.endswith('00'):
            continue
        if settlement != '000' and (settlement.endswith('00') or settlement.startswith('7')):
            continue

        code = region + district + settlement
        if code in names or not name.strip():
            raise ValueError(f'Некорректная запись ОКТМО {code} в строке {number}')
        names[code] = ' '.join(name.split())

    municipalities = []
    for code, name in sorted(names.items()):
        region = regions.get(code[:3] + '00000') or regions.get(code[:2] + '000000')
        if not region:
            raise ValueError(f'Не найден субъект для ОКТМО {code}')
        row = {'code': code, 'name': name, 'region': region}
        if not code.endswith('000'):
            parent = names.get(code[:5] + '000')
            if not parent:
                raise ValueError(f'Не найдено вышестоящее муниципальное образование для ОКТМО {code}')
            row['district'] = parent
        municipalities.append(row)

    required = set(regions.values()) - {'Байконур'}
    missing = required - {row['region'] for row in municipalities}
    if missing:
        raise ValueError('В выгрузке отсутствуют муниципалитеты: ' + ', '.join(sorted(missing)))
    return municipalities


def main():
    parser = argparse.ArgumentParser(description='Обновить JSON-справочник муниципальных образований по ОКТМО')
    parser.add_argument('--oktmo', default=OKTMO_URL, help='URL или путь к CSV ОКТМО')
    parser.add_argument('--regions', default=REGIONS_URL, help='URL или путь к CSV с названиями субъектов')
    parser.add_argument('--output', type=Path, default=OUTPUT_PATH, help='Путь к выходному JSON')
    args = parser.parse_args()

    try:
        municipalities = extract_municipalities(read_source(args.oktmo), region_names(read_source(args.regions)))
        rows = ',\n'.join('    ' + json.dumps(row, ensure_ascii=False) for row in municipalities)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text('{\n  "municipalities": [\n' + rows + '\n  ]\n}\n', encoding='utf-8', newline='\n')
    except (OSError, ValueError, KeyError, csv.Error) as error:
        parser.error(str(error))

    print(f'Муниципальных образований: {len(municipalities)}. Файл: {args.output}')


if __name__ == '__main__':
    main()
