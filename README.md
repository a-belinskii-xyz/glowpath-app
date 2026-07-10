# Mood Tracker

Multi-user REST API for daily mood logging. Built with FastAPI, PostgreSQL, and Docker Compose.

## Quick start (Docker)

```bash
cp .env.example .env          # Docker host ports (edit if 9000/5432/etc. are taken)
cp backend/.env.example backend/.env
docker compose up --build
```

Host ports are set in `.env` (`POSTGRES_PORT`, `APP_PORT`, `MINIO_API_PORT`, `MINIO_CONSOLE_PORT`, `MAILHOG_SMTP_PORT`, `MAILHOG_UI_PORT`). Defaults match the examples below.

- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- MinIO console: http://localhost:9001
- MailHog UI (dev email): http://localhost:8025

```bash
curl http://localhost:8000/v1/health
```

## Auth (stage 2)

Environment variables in `backend/.env` (see `backend/.env.example`):

- `JWT_SECRET_KEY` — required in production
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` — for Google OAuth
- `SMTP_*`, `EMAIL_FROM` — email delivery (MailHog in Docker: `SMTP_HOST=mailhog`, port `1025`)

### Email registration flow

```bash
# Register
curl -s -X POST http://localhost:8000/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"password123"}'

# Open the verification link from MailHog UI (http://localhost:8025) or email body.
# With APP_DEBUG=true, the link opens a simple HTML page at:
# http://localhost:8000/v1/dev/auth/verify-email?token=PASTE_TOKEN_HERE
# Or verify via API:
# curl -s "http://localhost:8000/v1/auth/verify-email?token=PASTE_TOKEN_HERE"

# Login
curl -s -X POST http://localhost:8000/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"password123"}'

# Current user
curl -s http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer PASTE_ACCESS_TOKEN"
```

### Password reset

```bash
curl -s -X POST http://localhost:8000/v1/auth/forgot-password \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'

# Open the reset link from MailHog UI (http://localhost:8025) or email body.
# With APP_DEBUG=true, the link opens a simple HTML form at:
# http://localhost:8000/v1/dev/auth/reset-password?token=PASTE_TOKEN_HERE
# Or reset via API:
# curl -s -X POST http://localhost:8000/v1/auth/reset-password \
#   -H 'Content-Type: application/json' \
#   -d '{"token":"PASTE_TOKEN_HERE","new_password":"newpassword99","password_confirm":"newpassword99"}'
```

### Google OAuth

1. Create OAuth credentials in [Google Cloud Console](https://console.cloud.google.com/).
2. Add authorized redirect URI: `http://localhost:8000/v1/auth/google/callback`
3. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `backend/.env`.

**Redirect flow (browser):**

```text
GET http://localhost:8000/v1/auth/google/login
→ Google consent → callback returns JSON with access_token
```

**ID token flow (API clients):**

```bash
curl -s -X POST http://localhost:8000/v1/auth/google \
  -H 'Content-Type: application/json' \
  -d '{"id_token":"GOOGLE_ID_TOKEN"}'
```

## Local development

`make` creates `backend/.venv` automatically (required on Debian/Ubuntu with PEP 668).

```bash
make install
cp backend/.env.example backend/.env
# Start PostgreSQL + MailHog (e.g. docker compose up db mailhog)
make migrate
make run
```

Integration tests require a running PostgreSQL with migrations applied (`make migrate`).

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
    core/         # security, OAuth, mood scale, i18n
    db/           # SQLAlchemy engine, session, Base
    models/       # ORM models
    schemas/      # Pydantic request/response models
    services/     # business logic
  alembic/        # database migrations
  tests/          # pytest
```
