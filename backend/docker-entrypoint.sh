#!/bin/sh
set -eu

if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
  alembic upgrade head
fi

# Built-in achievements and search tags; a failure must not keep the API down.
seed_builtin() {
  if [ "${SKIP_BUILTIN_SEED:-false}" != "true" ]; then
    python -m app.jobs.seed_builtin || echo "Built-in content seed failed, starting anyway" >&2
  fi
}

if [ "$#" -eq 0 ] || [ "${2:-}" = "app.main:app" ]; then
  seed_builtin
fi

if [ "${1:-}" = "uvicorn" ] && [ -n "${PORT:-}" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
fi

if [ "$#" -eq 0 ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

exec "$@"
