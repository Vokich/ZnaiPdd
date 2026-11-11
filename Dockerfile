FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY manage.py .
COPY pdd_site/ pdd_site/
COPY app/ app/

RUN python manage.py collectstatic --noinput \
    && groupadd --gid 10001 django \
    && useradd --uid 10001 --gid django --no-create-home django

USER django

CMD ["python", "-m", "uvicorn", "pdd_site.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
