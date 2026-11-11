# Reminders via cron-job.org

Render's free plan has no background workers, so the reminder worker from
`docker-compose.yml` does not run in production. Instead an external scheduler
(cron-job.org) calls the API every 5 minutes, and each call sends the reminders
that are due.

## How sending works

- `POST /v1/internal/reminders/tick` runs one pass: the same code as
  `python -m app.jobs.reminders --once`.
- A reminder is due from the user's chosen local time until
  `NOTIFICATIONS_MATCH_WINDOW_MINUTES` (default 30) after it. With a 5-minute
  tick it normally arrives 0–5 minutes after the chosen time, never before.
  If a tick is missed (cold start, timeout), the next one still sends it.
- Each schedule is sent at most once per day. Before delivering, a run claims
  the schedule by updating `last_sent_at` atomically, so overlapping ticks (or a
  tick plus the local worker) cannot send the same reminder twice. A failed
  delivery releases the claim and the next tick retries.
- The settings UI tells users that reminders arrive within 5 minutes after the
  chosen time.

## Idle ticks: Neon sleeps between reminders

Neon suspends its compute after about 5 minutes without queries. A tick that
read the schedules every 5 minutes kept it running around the clock, so each
tick now first asks an in-process cache (`app/services/notifications/due_cache.py`)
when the next reminder can be due:

- **Before that moment** the tick answers `"outcome": "idle"` and runs no SQL
  at all: no schedule query and no heartbeat write.
- **A full pass** (the old behaviour) runs after a process start, when the
  moment has come, after a change, or when the snapshot is older than
  `NOTIFICATIONS_DUE_CACHE_TTL_SECONDS` (default 6 h). After the pass it works
  out the next window start over all enabled schedules: local time, time zone,
  `days_of_week`, `interval_days`. Backoff is left out, so a person whose
  reminders are stretched costs one extra pass a day rather than a lost
  reminder. If a delivery failed and gave its claim back, the next tick runs a
  full pass again.
- **Changes reset the cache** through SQLAlchemy session events: any commit that
  touches `user_notification_schedules` (also bulk `UPDATE`/`DELETE`) or a user's
  `timezone`, `email`, `email_verified_at` or Telegram ids. New code that edits
  schedules needs no extra call.
- **One process only.** The cache lives in memory. Production runs one Render
  instance with one uvicorn process; with more processes a change made in one
  would reach the others only after the TTL. The Docker Compose worker is a
  separate process and always does a full pass.
- **"Sender works" status.** Idle ticks do not write the heartbeat row, so the
  settings status uses the fresher of that row and the last tick this process
  answered. Right after a deploy it can show "unavailable" until the first tick
  (at most 5 minutes).

## Endpoint

| | |
|---|---|
| URL | `https://mood-tracker-back.onrender.com/v1/internal/reminders/tick` |
| Method | `POST`, no body |
| Auth | `Authorization: Bearer <REMINDERS_CRON_SECRET>` |
| 200 | `{"outcome": "done" \| "idle" \| "feature_disabled" \| "worker_disabled", "users_considered", "daily_mood_sent", "goal_reminders_sent", "skipped", "errors", "next_due_at"}` |
| 401 | Missing or wrong secret |
| 404 | `REMINDERS_CRON_SECRET` is not set, so the endpoint is off |

Delivery errors for single users are logged and counted in `errors`, but the
response is still 200 so cron-job.org does not disable the job.

`next_due_at` is when the next full pass will run (UTC, `null` when no schedule
is enabled). Until then the answer is `idle` with zero counters.

## Render (API service)

| Variable | Value |
|---|---|
| `FEATURE_NOTIFICATIONS_ENABLED` | `true` |
| `REMINDERS_CRON_SECRET` | long random string, e.g. `openssl rand -hex 32` |
| `NOTIFICATIONS_POLL_INTERVAL_SECONDS` | `300` (the tick interval; drives the "sender is running" status in the UI) |
| `NOTIFICATIONS_DUE_CACHE_TTL_SECONDS` | optional, default `21600` (6 h): longest time between full passes |
| `TELEGRAM_BOT_TOKEN` | required for the Telegram channel |
| `SMTP_*`, `EMAIL_FROM` | required for the email channel |

## cron-job.org

1. Create a cronjob with the URL above.
2. Schedule: every 5 minutes, around the clock.
3. Advanced: request method `POST`, header `Authorization` = `Bearer <secret>`.
4. Save, then use "Test run" and expect HTTP 200 with `"outcome": "done"`
   (first call after a deploy) or `"idle"`, plus `next_due_at`.
5. About an hour later the Neon console should show the compute as **Idle**
   between reminders.

A request every 5 minutes also keeps the free API instance awake around the
clock (about 720 instance hours a month). Check the free-hours usage in the
Render dashboard, because the web and bot services share the same 750-hour
allowance; when it runs out Render suspends all free services until the next
month. If it gets tight, limit the cron job to the hours when reminders are set
(a reminder whose time falls outside those hours will then not arrive).

## Local development

`docker compose up` still runs the `reminders` worker, which polls every
`NOTIFICATIONS_POLL_INTERVAL_SECONDS`. To try the endpoint locally:

```bash
curl -X POST http://localhost:8000/v1/internal/reminders/tick \
  -H "Authorization: Bearer $REMINDERS_CRON_SECRET"
```
