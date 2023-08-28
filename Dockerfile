# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build wheels for every runtime dependency.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
 && apt-get install --no-install-recommends -y build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip wheel --wheel-dir /wheels -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime.  No compiler, no build headers, no root.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=GreetingApi.settings

RUN apt-get update \
 && apt-get install --no-install-recommends -y curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN python -m pip install --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

COPY --chown=app:app manage.py ./
COPY --chown=app:app GreetingApi ./GreetingApi
COPY --chown=app:app core ./core

# Writable location for the default SQLite file and collected static assets.
RUN mkdir -p /data /app/staticfiles && chown -R app:app /data /app/staticfiles
ENV DJANGO_DB_NAME=/data/db.sqlite3

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8000/healthz || exit 1

CMD ["gunicorn", "GreetingApi.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
