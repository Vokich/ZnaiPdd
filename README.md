# Знай ПДД

Сайт использует React и TypeScript, серверную часть Django и REST API по адресу `/api/`. Веб-клиент, API и Django Admin работают на одном домене.

## Локальный стенд

Запустите Docker Desktop и выполните из корня проекта.

```sh
docker compose -p znaipdd-dev --profile dev up --build -d
```

Сайт доступен на [localhost:5173](http://localhost:5173/), проверка API — на [localhost:5173/api/health/](http://localhost:5173/api/health/). Профиль `dev` хранит SQLite и медиа в собственных томах Docker. Знаки можно добавить через [Django Admin](http://localhost:5173/admin/).

```sh
docker compose -p znaipdd-dev --profile dev exec api-dev python manage.py test
```

Для разработки с автоматической синхронизацией файлов используйте `docker compose -p znaipdd-dev --profile dev up --build --watch`.

## Первый администратор

Укажите `DJANGO_SUPERUSER_USERNAME` и `DJANGO_SUPERUSER_PASSWORD` в локальном `.env`. Оба профиля Docker создают активного суперпользователя Django после миграций, перед запуском сервера. При повторном запуске пароль существующего суперпользователя сохраняется. Если логин уже занят другой учётной записью, задайте свободный логин. Когда обе переменные пусты, создание пропускается.

## Профиль prod

Скопируйте `.env.example` в `.env` при первичной настройке. Укажите `DJANGO_SECRET_KEY`, домен в ASCII или Punycode и существующие каталоги с SQLite и медиа. Для переноса действующей установки используйте текущие каталоги базы и медиа. Процесс Django работает с UID и GID `10001`, которому нужна запись в этих каталогах. Домен должен указывать на сервер, а порты 80 и 443 должны быть доступны для Caddy.

```sh
docker compose --profile prod up --build -d
```

Django применяет миграции при старте. Caddy отдаёт сборку React, обслуживает TLS и направляет запросы `/api/` и `/admin/` в Django. Существующие тома Caddy сохраняют сертификаты при обновлении контейнеров.
