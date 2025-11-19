#!/bin/sh
set -e

python manage.py migrate --noinput

INTERVAL="${INGEST_INTERVAL:-21600}"

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

run_ingest() {
  COMMAND=$(build_command)
  # shellcheck disable=SC2086
  sh -c "$COMMAND"
}

while true; do
  echo "[ingest-worker] Starting Met Office ingestion..."
  if run_ingest; then
    echo "[ingest-worker] Ingestion completed successfully."
  else
    echo "[ingest-worker] Ingestion failed (exit code $?)."
  fi
  echo "[ingest-worker] Sleeping for ${INTERVAL}s"
  sleep "$INTERVAL"
done

