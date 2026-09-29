# GlowPath

Telegram-first mood diary. The **Telegram Mini App** is the main UI, the **bot** is the entry point and reminder channel, and **FastAPI** (`/v1`) is the source of truth. The same React app also runs as a standalone website.

| | URL |
|--|--|
| Website / Mini App | https://mood-tracker-l17s.onrender.com |
| API | https://mood-tracker-back.onrender.com (`/docs`, `/health`) |

Deployment: [`docs/DEPLOY.md`](docs/DEPLOY.md). Local development: [`docs/development.md`](docs/development.md).

## Features

| Area | What it does |
|------|--------------|
| Mood entries | Several entries per day: score 1–5, date/time, markdown note (≤500 plain-text chars), tags, goals, up to 5 photos + 1 voice note |
| Custom mood scale | Per-user labels, colors and icons for each score; day backgrounds mixed from mood colors |
| Tags & tag groups | Per-user groups with `en`/`ru` labels, icons, reorder, pin to the entry form |
| Goals | Weekly / quantity goals with icons, shown on the entry form and in stats |
| Note templates | Reusable markdown snippets, seeded defaults |
| Entry composer | Configurable blocks on the entry form |
| Feed, calendar, stats | Paginated feed by date range in the user's timezone, month calendar, month mood index, month recap, streak |
| Gallery | All entry photos with lightbox |
| Semantic search | fastembed + pgvector over notes and voice transcriptions (off on Render) |
| Onboarding | Content packs of tags / templates / goals for new users |
| Auth | Telegram Mini App `initData`, Telegram browser login (OIDC), email + password with verification and reset, Google OAuth |
| Reminders | Schedules per kind (daily mood, goal tracking, weekly digest, custom) via email and/or Telegram; behind `FEATURE_NOTIFICATIONS_ENABLED` |
| Icon marketplace & wallet | Catalog packs bought with internal tokens; every balance change goes through `wallet_ledger` |
| Achievements | Catalog unlocks with token / pack / icon rewards |
| Plans | Spark (free) / Glow / Radiant; provider adapters `fake` (local), Stripe and Sber (scaffolds) |
| Staff console | `/staff`: users, ledger, token grants, official packs, presets |
| Guest local diary | Experiment: diary in IndexedDB without an account, see [`docs/guest-local-diary-experiment.md`](docs/guest-local-diary-experiment.md) |

## Stack

- **backend/**: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Postgres 16 + pgvector, S3-compatible storage (MinIO locally)
- **frontend/**: React + TypeScript + Vite; served by nginx in production, which proxies `/v1` to the API
- **telegram-bot/**: small FastAPI webhook service; talks to the API with a service token, never to the DB
- **reminders**: `python -m app.jobs.reminders`, a polling worker built from the backend image

## Quick start (local)

Requires Docker + Compose, Python 3.12+, Node 20+.

```bash
cp .env.example .env                  # host ports
cp backend/.env.example backend/.env  # app config, every variable is documented there
cp frontend/.env.example frontend/.env

make up                # API, Postgres+pgvector, MinIO, MailHog, reminders, telegram-bot
make frontend-install  # first time
make frontend-dev      # http://localhost:5173
```

| Service | URL |
|---------|-----|
| Frontend (Vite) | http://localhost:5173 |
| API / OpenAPI | http://localhost:8000 / http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |
| MailHog | http://localhost:8025 |
| Bot health | http://localhost:8081/health |

Ports come from the root `.env`. Demo data: `make seed`, then `make seed-marketplace` and `make seed-achievements` (in that order). Seed users are `alice@seed.moodtracker.dev` … with password `password123`.

Telegram Mini App and bot need public HTTPS tunnels locally; see [`docs/development.md`](docs/development.md#telegram). Auth flows, reminders, feature flags, demo data and operator CLIs are documented there too.

## Configuration

All backend settings live in `backend/app/config.py`; `backend/.env.example` lists them with comments. Feature flags follow one pattern: a master switch, a rollout percent, and allowlists.

| Flag | Default | Controls |
|------|---------|----------|
| `FEATURE_NOTIFICATIONS_ENABLED` | `false` | Reminder delivery and the settings UI |
| `FEATURE_ICON_MARKETPLACE` | `true` | Market and wallet |
| `FEATURE_ACHIEVEMENTS` | `true` | Achievements |
| `FEATURE_WEEKLY_FREQUENT_TAGS` | `false` | "Often this week" tag shortcuts |
| `FEATURE_GUEST_LOCAL_DIARY` | `false` | Guest experiment |
| `EMBEDDING_ENABLED` | `true` (`false` in the Docker image) | Semantic search |

Flags are read at process start: restart the API after changing them.

## Make targets

```bash
make install / reinstall         # backend venv
make lint / format / typecheck / test
make migrate / migrate-test / migrate-create MSG="..." / migrate-down REV=-1
make up / up-no-cache / down     # dev Compose
make up-prod / down-prod         # prod-shaped Compose (nginx UI on :8080)
make frontend-install / frontend-dev / frontend-build
make seed SEED_ARGS='--seed 42 --users 5 --days 45'
make seed-marketplace / seed-achievements
make wallet WALLET_ARGS='--help' # token grants with ledger, never UPDATE user_wallets by hand
make staff STAFF_ARGS='grant --user you@example.com'  # access to /staff
make preset-export PRESET=../preset.zip / preset-import PRESET=../preset.zip
make reindex-embeddings
make telegram-up / telegram-down # ngrok (bot webhook) + cloudflared (Mini App)
make pre-commit-install          # ruff, mypy, pytest before each commit
```

## Project layout

```text
backend/
  app/api/v1/    routes          app/services/  business logic
  app/models/    ORM             app/schemas/   Pydantic
  app/core/      domain rules    app/jobs/      reminders, reindex
  app/cli/       wallet, staff, presets
  app/data/      marketplace packs, achievement catalog
  alembic/       migrations      dev_seed/      local demo data
  tests/
frontend/src/    React app       frontend/nginx.conf.template
telegram-bot/    webhook service
docs/            deployment, development, feature notes
render.yaml      Render Blueprint
docker-compose.yml / docker-compose.prod.yml
```
