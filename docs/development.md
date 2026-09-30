# Development

Technical guide to GlowPath: stack, local setup, configuration, auth flows, reminders, Telegram, demo data and operator CLIs. Production deployment: [DEPLOY.md](DEPLOY.md).

## Stack

- **backend/**: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Postgres 16 + pgvector, S3-compatible storage (MinIO locally)
- **frontend/**: React + TypeScript + Vite; served by nginx in production, which proxies `/v1` to the API
- **telegram-bot/**: small FastAPI webhook service; talks to the API with a service token, never to the DB
- **reminders**: `python -m app.jobs.reminders`, a polling worker built from the backend image

## Quick start

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

Telegram Mini App and bot need public HTTPS tunnels locally; see [Telegram](#telegram) below.

## Configuration overview

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

## Backend without Docker

`make` creates `backend/.venv` automatically (required on Debian/Ubuntu with PEP 668).

```bash
make install
cp backend/.env.example backend/.env
docker compose up db mailhog minio   # dependencies only
make migrate
make run                             # uvicorn --reload on APP_PORT
```

Point `DATABASE_URL`, `SMTP_HOST` and `MINIO_ENDPOINT` in `backend/.env` at `localhost` and the ports from the root `.env`.

Tests use a separate database: `TEST_DATABASE_URL` must end with `_test` and differ from `DATABASE_URL`. `make migrate-test` prepares it, `make test` runs pytest.

`FRONTEND_URL` and `CORS_ORIGINS` in `backend/.env` must cover the UI origin. `localhost` and `127.0.0.1` are different CORS origins; the API adds loopback aliases automatically. Email links and OAuth redirects use `FRONTEND_URL`.

The frontend stores tokens in `localStorage` and refreshes them via `POST /v1/auth/refresh`.

## Auth flows

### Email registration

```bash
curl -s -X POST http://localhost:8000/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"password123"}'

# Open the verification link from MailHog (http://localhost:8025).
# With APP_DEBUG=true the link opens a simple page:
#   http://localhost:8000/v1/dev/auth/verify-email?token=PASTE_TOKEN_HERE
# Or verify via API:
#   curl -s "http://localhost:8000/v1/auth/verify-email?token=PASTE_TOKEN_HERE"

curl -s -X POST http://localhost:8000/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"password123"}'

curl -s http://localhost:8000/v1/auth/me -H "Authorization: Bearer PASTE_ACCESS_TOKEN"
```

### Password reset

```bash
curl -s -X POST http://localhost:8000/v1/auth/forgot-password \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'

# Link from MailHog. With APP_DEBUG=true:
#   http://localhost:8000/v1/dev/auth/reset-password?token=PASTE_TOKEN_HERE
# Or via API:
#   curl -s -X POST http://localhost:8000/v1/auth/reset-password \
#     -H 'Content-Type: application/json' \
#     -d '{"token":"PASTE_TOKEN_HERE","new_password":"newpassword99","password_confirm":"newpassword99"}'
```

### Google OAuth

1. Create OAuth credentials in [Google Cloud Console](https://console.cloud.google.com/).
2. Add the redirect URI `http://localhost:8000/v1/auth/google/callback`.
3. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `backend/.env`.

Browser flow: `GET /v1/auth/google/login`. API clients post an ID token:

```bash
curl -s -X POST http://localhost:8000/v1/auth/google \
  -H 'Content-Type: application/json' \
  -d '{"id_token":"GOOGLE_ID_TOKEN"}'
```

### Telegram browser login

"Continue with Telegram" uses OpenID Connect from BotFather → Login Widget. Set `TELEGRAM_OIDC_CLIENT_ID`, `TELEGRAM_OIDC_CLIENT_SECRET`, `TELEGRAM_OIDC_REDIRECT_URI` and register the redirect URI as an allowed URL. The `id` claim is the Telegram user id, the same as in Mini App `initData`.

## Reminders

Delivery is off unless `FEATURE_NOTIFICATIONS_ENABLED=true`; with it off the settings UI is locked. `NOTIFICATIONS_WORKER_ENABLED=false` pauses sending without stopping the worker.

Each user has one schedule per kind: `daily_mood`, `goal_tracking`, `weekly_digest`, `custom_reminder`.

```bash
curl -s http://localhost:8000/v1/notification-settings/status -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8000/v1/notification-settings -H "Authorization: Bearer $TOKEN"

# Daily mood reminder at 20:30 local time, email + Telegram
curl -s -X PATCH http://localhost:8000/v1/notification-settings/daily_mood \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled": true, "time_of_day": "20:30", "channels": ["email", "telegram"]}'
```

Other fields: `interval_days` (1–30) and `days_of_week` (0–6).

The Compose `reminders` service (`python -m app.jobs.reminders`) polls every `NOTIFICATIONS_POLL_INTERVAL_SECONDS` and sends within `NOTIFICATIONS_MATCH_WINDOW_MINUTES` after the scheduled local time. Email uses the `SMTP_*` settings; Telegram uses `TELEGRAM_BOT_TOKEN`.

Telegram reminders carry a Mini App button (`startapp=create_daily` or `goal_reminder`). An entry saved from a reminder stores `source` as `{channel}:{kind}` for analytics; it is not returned in public entry JSON.

## Feature flags

Flags are env variables read at process start; restart `app` after changing them. Each rollout flag has a master switch, a percent (stable hash bucket) and allowlists:

```bash
# Only allowlisted people
FEATURE_WEEKLY_FREQUENT_TAGS=true
FEATURE_WEEKLY_FREQUENT_TAGS_PERCENT=0
FEATURE_WEEKLY_FREQUENT_TAGS_EMAILS=you@example.com

# 20% of users plus the allowlist
FEATURE_WEEKLY_FREQUENT_TAGS_PERCENT=20

# Instant rollback
FEATURE_WEEKLY_FREQUENT_TAGS=false
```

The same pattern applies to `FEATURE_ICON_MARKETPLACE*`, `FEATURE_ACHIEVEMENTS*` and `FEATURE_GUEST_LOCAL_DIARY*` (see [guest-local-diary-experiment.md](guest-local-diary-experiment.md)). All variables are listed in `backend/.env.example`.

## Telegram

The bot receives updates over a webhook, so locally it needs a public HTTPS URL. The Mini App needs a second HTTPS URL for the frontend.

### Configure `backend/.env`

Create a bot with [@BotFather](https://t.me/BotFather), then set:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_BOT_USERNAME=your_bot_name
TELEGRAM_BOT_SERVICE_TOKEN=dev-telegram-bot-service-token
TELEGRAM_WEBHOOK_SECRET=dev-telegram-webhook-secret
TELEGRAM_WEBHOOK_PATH=/telegram/webhook
TELEGRAM_WEBHOOK_URL=       # tunnel base URL, no path
TELEGRAM_MINI_APP_URL=      # HTTPS origin of the frontend
```

On startup the bot calls `setWebhook` for `{TELEGRAM_WEBHOOK_URL}{TELEGRAM_WEBHOOK_PATH}`.

### Tunnels

With Vite running (`make frontend-dev`):

```bash
make telegram-up     # stop with make telegram-down
```

The script starts **ngrok** for the bot webhook (`:8081`) and a **cloudflared** quick tunnel for the Mini App (`:5173`), writes both URLs into `backend/.env`, empties `VITE_API_BASE_URL` in `frontend/.env` and recreates `app` and `telegram-bot`. Both `ngrok` and `cloudflared` must be installed. Quick tunnel URLs change every run: set BotFather **Menu Button** and **Main Mini App** to the printed Mini App URL, and restart Vite so it picks up the empty `VITE_API_BASE_URL`.

By hand, any HTTPS tunnel to `:8081` works as `TELEGRAM_WEBHOOK_URL` (`ngrok http 8081`, `ssh -R 80:localhost:8081 nokey@localhost.run`, `npx localtunnel --port 8081`). Restart `telegram-bot` afterwards; the log should show `Telegram webhook registered`.

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
curl http://localhost:8081/health
```

### New user flow

1. Send `/start` to the bot and tap **Open App**. The Mini App signs in from `initData` and opens `/onboarding`.
2. After onboarding, `/start` shows **Log mood** and **Open App**.
3. `/log` or **Log mood** opens the create screen (`startapp=create`). Save with the Telegram Main Button.
4. Optional: add an email in Profile to also sign in on the website.

Old links with `?start=log` open the Mini App create screen; the chat wizard is retired.

### Linking an existing website account

1. Profile → **Connect Telegram** creates a one-time code and a `t.me/…?start=…` link.
2. Open the link in Telegram (or send `/start <code>`).
3. Enable the Telegram channel in notification settings to get reminders in chat.

## Demo data

`backend/dev_seed/` fills Postgres and MinIO with deterministic demo users. It is local-only and has no API routes.

```bash
make seed
make seed SEED_ARGS='--seed 42 --users 5 --days 45'
cd backend && .venv/bin/python -m dev_seed --help
```

`make seed` uses `DATABASE_URL` from `backend/.env` and points `MINIO_ENDPOINT` at `localhost:$MINIO_API_PORT`. The same `--seed` gives the same content. Re-running deletes previous `*@seed.moodtracker.dev` users and their files. Personas log with realistic gaps (consistent, sparse, weekday-only, bursts…).

| Email | Password |
|-------|----------|
| `alice@seed.moodtracker.dev` … `evan@seed.moodtracker.dev` | `password123` |

Up to 8 personas with `--users`; see `backend/dev_seed/personas.py`.

Catalog data (needs the `app` container):

```bash
make seed-marketplace    # packs from backend/app/data/marketplace/, see its README
make seed-achievements   # backend/app/data/achievements/catalog.json; run after packs
```

After seeding or upgrading a database, backfill semantic-search vectors with `make reindex-embeddings` (requires `EMBEDDING_ENABLED=true`).

## Operator CLIs

Token balances change only through `wallet_ledger`; never `UPDATE user_wallets` by hand.

```bash
make wallet WALLET_ARGS='show --user you@example.com'
make wallet WALLET_ARGS='grant --user you@example.com --amount 500 --note beta'
make wallet WALLET_ARGS='reconcile --user you@example.com --note "manual DB +500"'
make wallet WALLET_ARGS='unlocks --user you@example.com'
make wallet WALLET_ARGS='revoke --user you@example.com --pack random-pics --note qa'
```

`grant` / `adjust` change the balance and write history. `reconcile` only records a balance already changed in SQL. `revoke` locks a bought pack and refunds it (`--no-refund` to skip).

```bash
make staff STAFF_ARGS='grant --user you@example.com'   # access to /staff
make staff                                             # list staff

# Catalog presets (packs + achievements) for another instance
make preset-export PRESET=../preset.zip PRESET_ARGS='--pack foxes --no-achievements'
make preset-import PRESET=../preset.zip
```

## Prod-shaped Compose locally

Serves the built frontend through nginx and proxies `/v1` to the API, without Vite or `--reload`:

```bash
make down
make up-prod     # creates .env.prod from .env.prod.example if missing
```

Open http://localhost:8080; MailHog stays on http://localhost:8025. `make down-prod` stops it. Postgres and storage are external here: fill `DATABASE_URL*` and `MINIO_*` in `.env.prod`. See [DEPLOY.md](DEPLOY.md) for running it on a server.

## Pre-commit

`make pre-commit-install` once per clone. Before each commit the hooks run ruff (format + lint), mypy and pytest. Run them manually with `make pre-commit`.
