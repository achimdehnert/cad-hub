# ===========================================================================
# CAD Hub Dockerfile (ADR-022 compliant)
# ===========================================================================
# Multi-stage build: builder → production
# Base: python:3.12-slim (Debian bookworm)
# User: app (UID 1000, non-root)
# Healthcheck: defined per-service in docker-compose.prod.yml (ADR-078)
# ===========================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install dependencies, compile wheels
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels \
    -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Production — minimal image, non-root user
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS production

ARG APP_NAME=cad-hub

LABEL org.opencontainers.image.source="https://github.com/achimdehnert/cad-hub"
LABEL org.opencontainers.image.description="CAD Hub — IFC/DXF Analysis Platform (ADR-022)"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/vendor

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --create-home app

COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

WORKDIR /app
COPY --chown=app:app . .

RUN SECRET_KEY=build-dummy-not-used-in-prod \
    DJANGO_SETTINGS_MODULE=config.settings.development \
    python manage.py collectstatic --noinput
RUN chown -R app:app /app/staticfiles

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
