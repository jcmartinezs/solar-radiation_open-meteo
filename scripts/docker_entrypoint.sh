#!/usr/bin/env bash
set -euo pipefail

MYSQL_HOST="${MYSQL_HOST:-db}"
MYSQL_PORT="${MYSQL_PORT:-3306}"

echo "Waiting for MySQL at ${MYSQL_HOST}:${MYSQL_PORT}..."
for i in $(seq 1 60); do
  if (echo >/dev/tcp/${MYSQL_HOST}/${MYSQL_PORT}) >/dev/null 2>&1; then
    echo "MySQL is reachable"
    break
  fi
  sleep 1
  if [ "$i" -eq 60 ]; then
    echo "MySQL did not become reachable in time" >&2
    exit 1
  fi
done

echo "Creating tables (init-db)..."
flask --app solar_radiation_api:create_app init-db

echo "Starting API (gunicorn) on :8000"
exec gunicorn -b 0.0.0.0:8000 wsgi:app
