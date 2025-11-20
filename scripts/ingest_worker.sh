#!/bin/sh
set -e

python manage.py migrate --noinput

build_command() {
  set -- python manage.py ingest_metoffice

  if [ -n "$INGEST_REGIONS" ]; then
    set -- "$@" --regions $INGEST_REGIONS
  fi

  if [ -n "$INGEST_PARAMETERS" ]; then
    set -- "$@" --parameters $INGEST_PARAMETERS
  fi

  echo "$@"
}

run_startup_ingest() {
  if [ "${RUN_INITIAL_INGEST:-1}" != "1" ]; then
    echo "[ingest-worker] Skipping startup ingestion."
    return 0
  fi

  COMMAND=$(build_command)
  echo "[ingest-worker] Triggering startup ingestion..."
  # shellcheck disable=SC2086
  if sh -c "$COMMAND"; then
    echo "[ingest-worker] Startup ingestion completed successfully."
  else
    echo "[ingest-worker] Startup ingestion failed." >&2
  fi
}

run_startup_ingest

CELERY_LOG_LEVEL=${CELERY_LOG_LEVEL:-info}
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-1}

echo "[ingest-worker] Starting Celery worker (loglevel=${CELERY_LOG_LEVEL}, concurrency=${CELERY_CONCURRENCY})"
exec celery -A config worker --loglevel="$CELERY_LOG_LEVEL" --concurrency="$CELERY_CONCURRENCY"