FROM python:3.13-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements/ requirements/
RUN python -m pip install --no-cache-dir --no-compile -c requirements/constraints.txt -r requirements/runtime.txt

COPY backend/ ./

RUN python manage.py collectstatic --noinput \
    && groupadd --gid 10001 django \
    && useradd --uid 10001 --gid django --no-create-home django \
    && mkdir -p /data /app/media \
    && chown -R django:django /data /app/media /app/app /app/pdd_site /app/templates

USER django

CMD ["python", "-m", "uvicorn", "pdd_site.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]

FROM node:24-alpine AS frontend-dev
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM frontend-dev AS frontend-build
RUN npm run build

FROM caddy:2.11-builder AS caddy-build
RUN xcaddy build "$CADDY_VERSION" --with github.com/mholt/caddy-ratelimit@5625512f24f6f59d6f64fb3aafe5eecff0b286db

FROM caddy:2.11-alpine AS frontend-prod
COPY --from=caddy-build /usr/bin/caddy /usr/bin/caddy
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend-build /frontend/dist/ /srv/frontend/
