# Mood Tracker

Multi-user REST API for daily mood logging. Built with FastAPI, PostgreSQL, and Docker Compose.

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

```bash
curl http://localhost:8000/v1/health
```

## Local development

`make` creates `backend/.venv` automatically (required on Debian/Ubuntu with PEP 668).

```bash
make install
cp backend/.env.example backend/.env
# Start PostgreSQL (e.g. docker compose up db)
make run
```

## Tooling

```bash
make install              # creates backend/.venv on first run; skips pip if already installed
make pre-commit-install   # install git hooks (run once per clone)
make lint
make typecheck
make test
make migrate              # alembic upgrade head
make migrate-create MSG="add users table"  # autogenerate migration
make migrate-down         # alembic downgrade -1 (or REV=base / REV=<revision>)
```

Before each `git commit`, pre-commit runs formatting (ruff), lint, mypy, and pytest. To run hooks manually: `make pre-commit`.

To force a clean reinstall: `make reinstall`

## Project layout

```text
backend/
  app/
    api/v1/       # versioned API routes
    core/         # shared utilities (auth, security, etc.)
    db/           # SQLAlchemy engine, session, Base
    models/       # ORM models
  alembic/        # database migrations
  tests/          # pytest
```
