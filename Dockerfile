FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 1000 app \
    && mkdir /data \
    && chown app /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Clave temporal: collectstatic no firma nada y la imagen no conserva este valor.
RUN DJANGO_SECRET_KEY=solo-para-construir python manage.py collectstatic --noinput

USER app

EXPOSE 8000

ENTRYPOINT ["sh", "docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4"]
