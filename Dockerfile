FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SECRET_KEY=docker-secret \
    DEBUG=0

ARG DATABASE_URL="postgresql://placeholder:placeholder@localhost:5432/dummy"
ENV DATABASE_URL=${DATABASE_URL}

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN chmod +x scripts/*.sh

RUN python manage.py collectstatic --noinput

CMD ["scripts/start_web.sh"]

