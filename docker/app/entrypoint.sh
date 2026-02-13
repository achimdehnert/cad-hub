#!/bin/bash
# ===========================================================================
# entrypoint.sh — CAD Hub (ADR-022)
# ===========================================================================
# Modes: web | worker | beat
# ===========================================================================
set -euo pipefail

: "${DJANGO_SETTINGS_MODULE:?ERROR: DJANGO_SETTINGS_MODULE must be set}"

if [ "${ENTRYPOINT_MIGRATE:-false}" = "true" ]; then
    echo "[entrypoint] Running migrations..."
    python manage.py migrate --noinput --skip-checks || exit 2
fi

MODE="${1:?ERROR: Usage: entrypoint.sh [web|worker|beat]}"

case "${MODE}" in
    web)
        echo "[entrypoint] Starting gunicorn (workers=${GUNICORN_WORKERS:-2}, timeout=${GUNICORN_TIMEOUT:-120})"
        exec gunicorn config.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers "${GUNICORN_WORKERS:-2}" \
            --timeout "${GUNICORN_TIMEOUT:-120}" \
            --access-logfile - \
            --error-logfile -
        ;;

    worker)
        echo "[entrypoint] Starting celery worker (concurrency=${CELERY_CONCURRENCY:-2})"
        exec celery -A config worker \
            -l "${CELERY_LOG_LEVEL:-info}" \
            --concurrency="${CELERY_CONCURRENCY:-2}"
        ;;

    beat)
        echo "[entrypoint] Starting celery beat"
        exec celery -A config beat \
            -l "${CELERY_LOG_LEVEL:-info}" \
            --schedule=/tmp/celerybeat-schedule
        ;;

    *)
        echo "ERROR: Unknown mode '${MODE}'. Usage: entrypoint.sh [web|worker|beat]" >&2
        exit 1
        ;;
esac
