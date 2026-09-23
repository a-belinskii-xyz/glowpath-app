#!/bin/sh
set -eu

if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
  alembic upgrade head
fi

if [ "${1:-}" = "uvicorn" ] && [ -n "${PORT:-}" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
fi

if [ "$#" -eq 0 ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

exec "$@"
