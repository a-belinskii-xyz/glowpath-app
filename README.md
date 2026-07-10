# Mood Tracker

Multi-user mood logging app: FastAPI backend + React frontend, PostgreSQL, and Docker Compose.

## Prerequisites

- **Docker** and **Docker Compose** — backend services (API, PostgreSQL, MinIO, MailHog)
- **Python 3.12+** — local backend development (`make install`, `make run`)
- **Node.js 20+** and **npm** — frontend dev server and build

## Quick start (full stack)

### 1. Environment files

```bash
cp .env.example .env              # Docker host ports
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env   # optional for now
```

Edit `.env` if ports are already in use (`POSTGRES_PORT`, `APP_PORT`, `MINIO_*`, `MAILHOG_*`).

### 2. Backend (Docker)

```bash
docker compose up --build
# or
make up
```

Wait until the API is up, then check:

```bash
curl http://localhost:8000/v1/health
```

### 3. Frontend (local dev server)

In a **second terminal**:

```bash
make frontend-install   # first time only
make frontend-dev
```

Open http://localhost:5173 — default Vite + React shell (no API wiring yet).

### Service URLs

| Service | URL |
|---------|-----|
| Frontend (dev) | http://localhost:5173 |
| API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| MinIO console | http://localhost:9001 |
| MailHog UI (dev email) | http://localhost:8025 |

Host ports come from root `.env` (defaults above).

## Frontend

Scaffold only — auth and mood CRUD will be added in follow-up steps.

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # output in frontend/dist/
npm run preview  # serve production build locally
```

From the repo root:

```bash
make frontend-install
make frontend-dev
make frontend-build
```

`frontend/.env.example`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

Copy to `frontend/.env` when you start calling the API.

### Roadmap

1. **Scaffold** (current) — empty React app, dev tooling
2. **Auth UI** — register, login, email verification, password reset, Google OAuth
3. **Mood CRUD** — entries, tags, attachments

## Backend quick start (Docker only)

```bash
cp .env.example .env
cp backend/.env.example backend/.env
docker compose up --build
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

## Local development (backend without Docker for the app)

`make` creates `backend/.venv` automatically (required on Debian/Ubuntu with PEP 668).

```bash
make install
cp backend/.env.example backend/.env
# Start PostgreSQL + MailHog (e.g. docker compose up db mailhog minio)
make migrate
make run
```

Integration tests require a running PostgreSQL with migrations applied (`make migrate`).

Typical full-stack local workflow:

```text
Terminal 1: docker compose up db mailhog minio app   # or make up
Terminal 2: make frontend-dev
```

## Tooling

```bash
make install              # backend: creates .venv on first run
make pre-commit-install   # install git hooks (run once per clone)
make lint
make typecheck
make test
make migrate              # alembic upgrade head
make migrate-create MSG="add users table"
make migrate-down         # alembic downgrade -1 (or REV=base / REV=<revision>)
make frontend-install
make frontend-dev
make frontend-build
```

Before each `git commit`, pre-commit runs formatting (ruff), lint, mypy, and pytest. To run hooks manually: `make pre-commit`.

To force a clean backend reinstall: `make reinstall`

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
frontend/
  src/            # React app (Vite + TypeScript)
  public/         # static assets
docker/           # Postgres init scripts
```
