# Справочник муниципалитетов

Сайт читает `app/data/municipalities.json`. В файле 13 803 муниципальных образования из 89 регионов по выгрузке от 8 сентября 2026 года. Для поселений и внутригородских районов сохраняется название вышестоящего муниципального образования, если оно есть в ОКТМО.

- Коды и названия: [ОКТМО Росстата](https://rosstat.gov.ru/opendata/7708234640-oktmo?source=subscribe), [копия CSV на Classifikators.ru](https://classifikators.ru/assets/downloads/oktmo/oktmo.csv).
- Названия регионов приведены к именительному падежу по справочнику [«Регионы России» HFLabs](https://github.com/hflabs/region), [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

[Открытый GeoJSON от CEBPM](https://huggingface.co/datasets/CEBPM/Municipalities-of-Russia/tree/main) содержит 2 674 записи. Чтобы включить поселения и другие муниципальные образования из полного классификатора, JSON для сайта собирается из CSV ОКТМО.

Чтобы пересобрать JSON из опубликованных CSV, запустите из корня проекта:

```powershell
python scripts/update_municipalities.py
```

Для локальной или более свежей выгрузки ОКТМО укажите путь или HTTPS-ссылку через `--oktmo`. Для локальной копии файла HFLabs укажите `--regions`:

```powershell
python scripts/update_municipalities.py --oktmo .\oktmo.csv --regions .\region.csv
```

После обновления перезапустите Django: справочник кэшируется в памяти процесса. Миграции базы данных не требуются.
