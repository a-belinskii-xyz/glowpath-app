# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

GlowPath is a mood diary that runs as a website and as a Telegram Mini App. It has three deployable parts: `backend/` (FastAPI API), `frontend/` (React SPA) and `telegram-bot/` (webhook bot). Fuller references:

- `docs/development.md`: local setup, env vars, auth flows, reminders, Telegram tunnels, operator CLIs
- `docs/architecture.md`: how the parts connect and the trade-offs behind them
- `docs/DEPLOY.md`: Render, Neon and production env
- `docs/guest-local-diary-experiment.md`, `docs/reminders-cron.md`: notes on single features

## Commands

Run from the repo root. The Makefile creates `backend/.venv` and calls tools as `backend/.venv/bin/...`, so it needs a POSIX shell with `make` (Linux, macOS or WSL). Without `make`, run the same tools from `backend/` directly.

```bash
make up                       # dev stack: API :8000, Postgres+pgvector, MinIO, MailHog, reminders worker, bot
make install                  # backend venv with dev extras
make lint / format / typecheck / test
make migrate                  # alembic upgrade head on DATABASE_URL
make migrate-test             # same, on the test database
make migrate-create MSG="..." # autogenerate a revision
make frontend-install / frontend-dev / frontend-build
make pre-commit-install       # hooks: ruff format + lint, mypy, full pytest
```

**Backend tests**
- Tests need Postgres. `docker compose up db` creates `mood_tracker_test` through `docker/postgres/init/`. Run `make migrate-test` after adding migrations: tests do not create the schema.
- If Postgres is unreachable, DB-backed tests are **skipped, not failed**. Check the skip count before trusting a green run.
- `tests/db_safety.py` refuses to run unless `TEST_DATABASE_URL` ends in `_test` and differs from `DATABASE_URL`.
- Each test runs inside a transaction that is rolled back.
- The `auth_client` fixture overrides DB, email (`FakeEmailService` with `.outbox`) and storage (`FakeStorage`). `register_verify_and_login()` in `tests/conftest.py` returns an access token.

Run a single test:

```bash
cd backend && TEST_DATABASE_URL=postgresql+psycopg://mood:mood@localhost:5432/mood_tracker_test \
  .venv/bin/pytest tests/test_goals.py::test_name -x
```

**Frontend**
- `npm run lint` checks style.
- `npm run build` runs `tsc -b`, so it is the typecheck.
- There is no frontend test suite.

**Telegram bot**
- No make target and no pre-commit hook. Run `cd telegram-bot && pip install -e ".[dev]" && pytest`.

**CI**
- There is no CI. Before merging, run `make lint typecheck test` and `make frontend-build`.

## Architecture

### Backend layering (`backend/app/`)
- `api/v1/*.py` routes are thin, synchronous `def` endpoints. They use sync SQLAlchemy with one session per request (`db/session.get_db`). Production goes through the Neon PgBouncer pooler in transaction mode, so prepared statements are off.
- `services/` holds the business logic, and `core/` holds pure domain rules (mood scale, streaks, feature flags, i18n, error codes).
- Services raise subclasses of `AppError` (`core/errors.py`) that carry an `ErrorCode`. Routes catch them and call `raise_http_error`.
- Error responses look like `{"detail": {"code", "message", "params"}}`. Codes are snake_case values in `core/error_codes.py`. The frontend maps each one to `apiErrors.<camelCase>` in `frontend/src/i18n/messages.ts`, so a new code needs an `en` and a `ru` message there.
- Auth dependencies live in `api/deps.py`:
  - `get_current_user`
  - `get_current_verified_user` (most diary endpoints use this one)
  - `get_current_staff_user`
  - `require_telegram_bot_service` (checks the bot's `X-Telegram-Bot-Service-Token`)
- Email and object storage are injected (`get_email_service`, `get_storage_service`) so tests can swap them out. Attachments sit in S3/MinIO and the API streams them back after an ownership check.

### Database and migrations
- Build table names with `db/names.table_name()`. It adds `DB_TABLE_PREFIX` (default `mt_`).
- Constraint and index names come from the naming convention in `db/base.py`. Import every new model in `app/models/__init__.py`, or `alembic --autogenerate` will not see it.
- Migration files are named `<epoch>_<rev>_<slug>.py`. `tests/test_migration_heads.py` requires a single head and unique revision ids.
- `tests/migrations/test_stairway.py` runs upgrade, downgrade and upgrade again for every revision, so every `downgrade()` must work.
- The API container runs `alembic upgrade head` on every start (`backend/docker-entrypoint.sh`), and then seeds built-in achievements (`app.jobs.seed_builtin`). A new migration must therefore work alongside the previous release's code. Split destructive schema changes across two releases.

### Cross-cutting rules
- **Feature flags** (`core/feature_flags.py`): each flag has a master switch, a percent rollout (stable hash of flag + user id) and email/user-id allowlists. Use `is_feature_enabled_for_user` or `features_for_user` to check them. Flags come from env at process start, so restart after changing them.
- **i18n**: `en` and `ru` everywhere.
  - Backend: `core/i18n.py` picks the locale from `?locale=` or `Accept-Language`, and localized labels are `LocaleLabels` dicts.
  - Frontend: `ru` is typed as `DeepStringLeaves<typeof en>`, so a missing translation fails the build.
  - The bot has its own `bot/i18n.py`.
- **Reminders**: `python -m app.jobs.reminders` (the local worker) and `POST /v1/internal/reminders/tick` (cron-job.org in production) run the same pass. Duplicate sends are prevented by an atomic claim on `last_sent_at`. The HTTP tick answers `idle` without any SQL until the next reminder can be due (`services/notifications/due_cache.py`, reset by session events on schedule and user changes), so production must stay one API process. Reminder text lives only in `core/companion.py` and `core/notification_copy.py`. Backoff logic is in `services/notifications/backoff.py`.
- **Wallet**: token balances change only through `wallet_ledger` (`wallet_service` or `make wallet`). Never update `user_wallets` directly.
- **Diary export format** (`services/diary_archive/`): to change it, bump `CURRENT_VERSION` and add one step to `UPGRADES`. Never edit a step that has already shipped, and keep a fixture of every old version in `tests/fixtures/`.
- **Sentry** deliberately sends no PII, request bodies, frame locals or logs, and `tests/test_sentry.py` enforces this. An empty DSN disables it, and `backend/conftest.py` forces an empty DSN for pytest.

### Frontend (`frontend/src/`)
- `api/*.ts` modules wrap `api/client.ts`. The client adds the bearer token and locale headers, and on a 401 it refreshes the token once and retries.
- In dev, Vite proxies `/v1` to `:8000`. In production, nginx serves the build and proxies `/v1`, so the app is same-origin.
- **Guest mode:** API functions for entries, goals, tags and similar first check `isGuestDiaryMode()`. If it is true, they read and write the IndexedDB store in `guest/store.ts` instead of the server. When you change one of these functions, update the guest branch too.
- Telegram Mini App code (initData, MainButton, start params, navigation) is in `platform/`. Theme and mood colours are in `design/`.

### Telegram bot (`telegram-bot/bot/`)
- The bot is a stateless webhook service. It talks to the API through `api_client.py` with the service token and never touches the database.
- On startup it registers its own webhook.

## Conventions

- Work is tracked as tasks `GP-N`.
  - Branch: `GP-N-<short-slug>`
  - PR title: `GP-N: ...`
  - Commit messages usually follow `GP-N: <lowercase summary>`.
  - One task per branch. Follow-up work after a merge becomes a new task.
- Ruff uses a line length of 100. Mypy runs in `strict` mode on `app/`.
