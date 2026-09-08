# GlowPath

Multi-user mood logging app (**GlowPath**, mark `glowpath:\`): FastAPI backend + React frontend, PostgreSQL, and Docker Compose.

Product naming / branding notes: [`docs/branding-naming-plan.md`](docs/branding-naming-plan.md).

## Features

| Feature | What it does |
|---------|----------------|
| Email registration & login | Create an account with email/password; JWT access + refresh tokens |
| Email verification | Confirm email via link (MailHog in local Docker); resend if needed |
| Password reset | Request a reset email and set a new password |
| Google OAuth | Sign in with Google (browser redirect or ID token for API clients) |
| Mood entries (CRUD) | Log several entries per day: score 1–5, date/time, markdown note (≤500 plain-text chars) |
| Tags & tag groups | Per-user groups and tags with `en`/`ru` labels; create, edit, reorder, delete; pin groups on the entry form |
| Attachments | Up to 5 photos + 1 audio per entry, stored in MinIO |
| Note templates | Reusable markdown snippets for notes; CRUD + reorder; seeded defaults for new users |
| Entry list & filters | Paginated feed filtered by date range in the user’s timezone; soft day backgrounds mixed from mood colors (see Mood Tracker.md) |
| Semantic search | Vector search over notes (and voice transcriptions when present) via local fastembed + pgvector; search box on the entries page |
| Month calendar | Calendar of days with entries; jump to a day in the list |
| Mood stats | Month mood index and month-over-month comparison (bar chart on home) |
| Profile & locale | View account info; switch UI language (`en` / `ru`); IANA timezone on the user |
| Reminders | Opt-in daily mood + weekly goal reminders (email and/or Telegram Mini App buttons; time + channels in settings) |
| Telegram bot | Mini App is the UI; bot is entry, `/log` deep link, reminders; webhook on `:8081` |
| Multi-user isolation | Each user’s entries, tags, templates, and files are private |
| Guest local diary (experiment) | Optional treatment cohort: diary in IndexedDB without account; sync only on **new** registration — see [`docs/guest-local-diary-experiment.md`](docs/guest-local-diary-experiment.md) |
| Freemium plans | Spark (free) / Glow / Radiant catalog, subscriptions, payment-provider adapters (`fake` locally; Stripe and Sber scaffolds) |
| Dev seed data | Deterministic demo users/entries/attachments for local UI work (`make seed`) |

## Prerequisites

- **Docker** and **Docker Compose** — backend services (API, PostgreSQL with pgvector, MinIO, MailHog)
- **Python 3.12+** — local backend development (`make install`, `make run`)
- **Node.js 20+** and **npm** — frontend dev server and build

Compose uses the `pgvector/pgvector:pg16` image so semantic search can store note embeddings in Postgres.
## Quick start (full stack)

### 1. Environment files

```bash
cp .env.example .env              # Docker host ports
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `.env` if ports are already in use (`POSTGRES_PORT`, `APP_PORT`, `MINIO_*`, `MAILHOG_*`, `TELEGRAM_BOT_PORT`).

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

Open http://localhost:5173 — register, log in, view profile, verify email, reset password.

Ensure `backend/.env` includes `FRONTEND_URL=http://localhost:5173` and `CORS_ORIGINS` covering the UI origin (see `backend/.env.example`). `localhost` and `127.0.0.1` are different CORS origins; the API adds loopback aliases automatically. Email links and Google OAuth redirect use `FRONTEND_URL`.

### Service URLs

| Service | URL |
|---------|-----|
| Frontend (dev) | http://localhost:5173 |
| API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| MinIO console | http://localhost:9001 |
| MailHog UI (dev email) | http://localhost:8025 |
| Telegram bot health | http://localhost:8081/health |

Host ports come from root `.env` (defaults above).

Compose also runs a **`reminders`** worker (email / Telegram) and a **`telegram-bot`** webhook service (port `TELEGRAM_BOT_PORT`, default `8081`).

## Frontend

React app with routing wired to the API.

| Route | Purpose |
|-------|---------|
| `/` | Landing (guests) or entries home: calendar, stats, feed (signed in) |
| `/register` | Email registration |
| `/login` | Email login + Google OAuth |
| `/entries/new` | Create mood entry |
| `/entries/:id` | Entry detail |
| `/entries/:id/edit` | Edit mood entry |
| `/tags` | Manage tag groups and tags |
| `/templates` | Manage note templates |
| `/profile` | Current user (`GET /v1/auth/me`), language switch |
| `/plans` | Freemium plans (Spark / Glow / Radiant) and checkout |
| `/verify-email?token=…` | Email verification (link from MailHog) |
| `/resend-verification` | Resend verification email |
| `/forgot-password` | Request password reset |
| `/reset-password?token=…` | Set new password |
| `/auth/google/callback` | Google OAuth return (redirect from backend) |

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

Copy to `frontend/.env`. Tokens are stored in `localStorage`; the client refreshes access tokens via `POST /v1/auth/refresh`.

### Roadmap

1. ~~**Scaffold**~~ — React app, dev tooling
2. ~~**Auth UI**~~ — register, login, email verification, password reset, Google OAuth
3. ~~**Mood CRUD**~~ — entries, tags, attachments, templates, calendar, month stats
4. **Deploy** — prod Compose locally → VPS + HTTPS (see below)

**VPS cheat sheet** (SSH, rsync, env, updates): [`docs/vps-cheatsheet.md`](docs/vps-cheatsheet.md).

### Prod-shaped Compose (UI in nginx)

One command serves the built frontend and proxies `/v1` to the API (no Vite, no `--reload`):

```bash
make down          # stop the dev stack first
cp .env.prod.example .env.prod
make up-prod       # docker compose -f docker-compose.prod.yml … --profile mail
```

Open http://localhost:8080. MailHog UI stays on http://localhost:8025 when using `--profile mail`.

`make down-prod` stops this stack. On a VPS, drop `--profile mail`, set real `SMTP_*` / `PUBLIC_URL`, and put TLS in front (stage C). Full remote steps: [`docs/vps-cheatsheet.md`](docs/vps-cheatsheet.md).

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
- `NOTIFICATIONS_WORKER_ENABLED` — master switch for the reminder worker (default `true`)
- `NOTIFICATIONS_POLL_INTERVAL_SECONDS` — how often the worker checks due reminders (default `60`)
- `NOTIFICATIONS_MATCH_WINDOW_MINUTES` — local-time window after the user’s reminder time (default `2`)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` — BotFather token and bot username (without `@`)
- `TELEGRAM_BOT_SERVICE_TOKEN` — shared secret for `telegram-bot` → API (`/v1/telegram/bot/*`)
- `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_WEBHOOK_PATH`, `TELEGRAM_WEBHOOK_URL` — webhook auth and public HTTPS base URL (see [Telegram bot](#telegram-bot-local-webhook))
- `TELEGRAM_MINI_APP_URL` — public HTTPS origin of the Mini App (BotFather Main Mini App / Open App button)
- `TELEGRAM_INIT_DATA_MAX_AGE_SECONDS` — Mini App `initData` replay window (default `86400`)
- `TELEGRAM_LINK_CODE_EXPIRE_MINUTES` — one-time Profile link code TTL (default `15`)
- `ENTRY_VISIBLE_TAG_GROUP_LIMIT` — max tag groups pinned to the entry form (default `6`; rest under “Other”)
- `ENTRY_VISIBLE_GOAL_LIMIT` — max goals pinned to the entry form (default `3`)
- `STATS_VISIBLE_GOAL_LIMIT` — max goals shown in calendar and period stats (default `5`)
- `FEATURE_WEEKLY_FREQUENT_TAGS` — master switch for “often this week” tag shortcuts (default `false`; instant rollback)
- `FEATURE_WEEKLY_FREQUENT_TAGS_PERCENT` — percent of users in a stable hash bucket (`0` = allowlists only, `100` = everyone)
- `FEATURE_WEEKLY_FREQUENT_TAGS_EMAILS` — comma-separated emails always included when the master switch is on
- `FEATURE_WEEKLY_FREQUENT_TAGS_USER_IDS` — comma-separated user UUIDs always included when the master switch is on
- `FEATURE_WEEKLY_FREQUENT_TAGS_LIMIT` — how many frequent tags to show (default `8`)
- `FEATURE_WEEKLY_FREQUENT_TAGS_DAYS` — lookback window in local calendar days (default `7`)

Restart the `app` container after changing these (env is loaded at process start; targeting should later move to a DB table). Examples:

```bash
# Only allowlisted people (try it on yourself first)
FEATURE_WEEKLY_FREQUENT_TAGS=true
FEATURE_WEEKLY_FREQUENT_TAGS_PERCENT=0
FEATURE_WEEKLY_FREQUENT_TAGS_EMAILS=you@example.com,friend@example.com

# 20% of users (stable per account) plus the allowlist
FEATURE_WEEKLY_FREQUENT_TAGS_PERCENT=20

# Everyone
FEATURE_WEEKLY_FREQUENT_TAGS_PERCENT=100

# Instant rollback
FEATURE_WEEKLY_FREQUENT_TAGS=false
```

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

### Notifications (reminders)

Users must **opt in** via `GET` / `PATCH /v1/notification-settings`:

- `enabled` — master switch
- `channels` — delivery channels (`email` on the website; Telegram-native accounts default to `telegram`)
- `daily_mood_reminder_enabled` + `daily_mood_reminder_time` — local time (user timezone) for the daily “log your mood” reminder
- `goal_reminders_enabled` — nudge when weekly goals are behind (same local time)

The Compose `reminders` service (or `python -m app.jobs.reminders`) polls every `NOTIFICATIONS_POLL_INTERVAL_SECONDS` and sends only inside `NOTIFICATIONS_MATCH_WINDOW_MINUTES` after the chosen time. SMTP uses the same `SMTP_*` / `EMAIL_FROM` settings as auth mail; Telegram uses `TELEGRAM_BOT_TOKEN`.

Daily mood emails link to `/entries/new?from=email:daily_mood_reminder`. Telegram reminders include a Mini App button (`startapp=create_daily` or `goal_reminder`) so the tap opens the matching screen. When the user saves an entry from that flow, the API stores `source` as `{channel}:{kind}` (e.g. `email:daily_mood_reminder`, `telegram:daily_mood_reminder`) for analytics — not returned in public entry JSON / not shown in UI.

```bash
# Enable daily mood + goal reminders at 20:30 local time (email + Telegram if linked)
curl -s -X PATCH http://localhost:8000/v1/notification-settings \
  -H "Authorization: Bearer PASTE_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "enabled": true,
    "channels": ["email", "telegram"],
    "daily_mood_reminder_enabled": true,
    "daily_mood_reminder_time": "20:30:00",
    "goal_reminders_enabled": true
  }'
```

### Telegram bot (local webhook)

Compose runs `telegram-bot` on port **8081** (see `TELEGRAM_BOT_PORT` in root `.env`). The bot receives Telegram updates over a **webhook**. On your laptop that requires a **public HTTPS URL** pointing at the bot — without it, Profile “Connect Telegram” opens the bot, but `/start <code>` never reaches the container and nothing happens.

Design notes: [`docs/telegram-integration-plan.md`](docs/telegram-integration-plan.md).

#### 1. Configure `backend/.env`

Create a bot with [@BotFather](https://t.me/BotFather), then set:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_BOT_USERNAME=your_bot_name
TELEGRAM_BOT_SERVICE_TOKEN=dev-telegram-bot-service-token
TELEGRAM_WEBHOOK_SECRET=dev-telegram-webhook-secret
TELEGRAM_WEBHOOK_PATH=/telegram/webhook
# Set after you start a tunnel (step 2):
TELEGRAM_WEBHOOK_URL=
# Public HTTPS origin of the frontend Mini App (BotFather + Open App button):
TELEGRAM_MINI_APP_URL=
```

`TELEGRAM_WEBHOOK_URL` is the tunnel **base** URL only (no path). On startup the bot calls `setWebhook` for `{TELEGRAM_WEBHOOK_URL}{TELEGRAM_WEBHOOK_PATH}`.

Mini App: in [@BotFather](https://t.me/BotFather) set **Menu Button** and **Main Mini App** to `TELEGRAM_MINI_APP_URL` (HTTPS). New users open the app there and are signed in with Telegram — no website account required.

For local Mini App testing you need a **second HTTPS tunnel to the frontend** (Vite `:5173` or prod nginx). Set `frontend/.env` to `VITE_API_BASE_URL=` (empty) so the WebView calls `/v1` on the same origin; Vite proxies `/v1` to the API. Put that frontend HTTPS origin in `TELEGRAM_MINI_APP_URL` and `CORS_ORIGINS`.

#### 2. Expose localhost:8081 with a tunnel

**cloudflared** (recommended; often works where ngrok needs a VPN):

```bash
# Install (Ubuntu/WSL amd64)
curl -L --output /tmp/cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i /tmp/cloudflared.deb
cloudflared --version

# Run tunnel (leave this terminal open)
cloudflared tunnel --url http://localhost:8081
```

Copy the printed HTTPS URL (e.g. `https://….trycloudflare.com`) into `backend/.env`:

```env
TELEGRAM_WEBHOOK_URL=https://….trycloudflare.com
```

Restart `telegram-bot` (or `make up`). Logs should show `Telegram webhook registered: …/telegram/webhook`.

**Alternatives** (no cloudflared install):

```bash
# SSH tunnel — URL appears in the terminal
ssh -R 80:localhost:8081 nokey@localhost.run

# Or, if Node.js is available
npx localtunnel --port 8081
```

Use the printed HTTPS URL as `TELEGRAM_WEBHOOK_URL` the same way.

#### 3. Link an account

1. Open Profile → **Connect Telegram** (creates a one-time code + `t.me/…?start=…` link).
2. Open the link in Telegram (or send `/start <code>` to the bot).
3. You should get a confirmation message; Profile should show the account as linked.
4. Enable the **Telegram** channel under notification settings if you want reminders in chat.

#### 4. Log mood from the bot

The chat wizard is retired. Mood is logged in the Mini App:

1. Send **`/log`**, or tap **Log mood** under `/start`. That opens create (`startapp=create`).
2. Daily reminders use `https://t.me/<bot>?startapp=create_daily` (same create screen, with reminder attribution).
3. Save with Telegram **Main Button**. Back Button returns to the dashboard.

Old reminder links with `?start=log` still work: they open the Mini App create screen instead of the chat wizard.

Check webhook registration:

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

Bot health (no Telegram required):

```bash
curl http://localhost:8081/health
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

## Mock seed data (local only)

`backend/dev_seed/` fills Postgres + MinIO with deterministic demo users for UI work. It is **not** part of the app runtime (no API routes).

Requires a running DB and MinIO (e.g. `make up`). `make seed` uses `DATABASE_URL` from `backend/.env` and overrides `MINIO_ENDPOINT` to `localhost:$(MINIO_API_PORT)` from the root `.env` so it works from the host against Compose.

Icon catalog packs are seeded separately: put folders of images in `backend/app/data/marketplace/<pack>/` and run `make seed-marketplace` (needs the `app` container). See that folder's README.

Token balance must go through `wallet_ledger` (never `UPDATE` `user_wallets` by hand). Operator CLI:

```bash
make wallet WALLET_ARGS='show --user you@example.com'
make wallet WALLET_ARGS='grant --user you@example.com --amount 500 --note beta'
make wallet WALLET_ARGS='reconcile --user you@example.com --note "manual DB +500"'
make wallet WALLET_ARGS='unlocks --user you@example.com'
make wallet WALLET_ARGS='revoke --user you@example.com --pack random-pics --note qa'
docker compose exec -T app python -m app.cli.wallet --help
```

`grant` / `adjust` change the balance and write history. `reconcile` only writes a ledger row for a balance you already changed in SQL. `revoke` locks a bought pack and refunds what they paid (`--no-refund` to skip).

After upgrading an existing database (or seeding), backfill semantic-search vectors:

```bash
make reindex-embeddings
```

```bash
make seed
# or with options:
make seed SEED_ARGS='--seed 42 --users 5 --days 45'
cd backend && .venv/bin/python -m dev_seed --help
```

Same `--seed` → same content (notes, scores, entry times, attachment presence). Re-running deletes previous `*@seed.moodtracker.dev` users and their MinIO objects, then recreates them.

Days are **not** filled solidly: each persona has a logging style (consistent, sparse, weekday-only, bursts, reflective, …) with realistic gaps.

| Email | Password |
|-------|----------|
| `alice@seed.moodtracker.dev` | `password123` |
| `bob@seed.moodtracker.dev` | `password123` |
| `carol@seed.moodtracker.dev` | `password123` |
| `diana@seed.moodtracker.dev` | `password123` |
| `evan@seed.moodtracker.dev` | `password123` |

(Up to 8 personas if you raise `--users`; see `backend/dev_seed/personas.py`.)

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
make seed                 # local mock users/entries/attachments
make seed-marketplace     # folder packs from backend/app/data/marketplace/
make wallet WALLET_ARGS='--help'  # grant/adjust/reconcile/revoke tokens with ledger
make reindex-embeddings   # backfill note embeddings for semantic search
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
    cli/          # operator CLIs (wallet ledger)
    core/         # security, OAuth, mood scale, i18n
    db/           # SQLAlchemy engine, session, Base
    models/       # ORM models
    schemas/      # Pydantic request/response models
    services/     # business logic
  dev_seed/       # local-only mock data CLI (not production)
  alembic/        # database migrations
  tests/          # pytest
frontend/
  src/            # React app (Vite + TypeScript)
  public/         # static assets
telegram-bot/     # Telegram webhook service (separate Compose container)
docs/             # design notes (e.g. Telegram integration plan)
docker/           # Postgres init scripts
```
