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

## Endpoint

| | |
|---|---|
| URL | `https://mood-tracker-back.onrender.com/v1/internal/reminders/tick` |
| Method | `POST`, no body |
| Auth | `Authorization: Bearer <REMINDERS_CRON_SECRET>` |
| 200 | `{"outcome": "done" \| "feature_disabled" \| "worker_disabled", "users_considered", "daily_mood_sent", "goal_reminders_sent", "skipped", "errors"}` |
| 401 | Missing or wrong secret |
| 404 | `REMINDERS_CRON_SECRET` is not set, so the endpoint is off |

Delivery errors for single users are logged and counted in `errors`, but the
response is still 200 so cron-job.org does not disable the job.

## Render (API service)

| Variable | Value |
|---|---|
| `FEATURE_NOTIFICATIONS_ENABLED` | `true` |
| `REMINDERS_CRON_SECRET` | long random string, e.g. `openssl rand -hex 32` |
| `NOTIFICATIONS_POLL_INTERVAL_SECONDS` | `300` (the tick interval; drives the "sender is running" status in the UI) |
| `TELEGRAM_BOT_TOKEN` | required for the Telegram channel |
| `SMTP_*`, `EMAIL_FROM` | required for the email channel |

## cron-job.org

1. Create a cronjob with the URL above.
2. Schedule: every 5 minutes, around the clock.
3. Advanced: request method `POST`, header `Authorization` = `Bearer <secret>`.
4. Save, then use "Test run" and expect HTTP 200 with `"outcome": "done"`.

A request every 5 minutes also keeps the free API instance awake around the
clock (about 720 instance hours a month). Check the free-hours usage in the
Render dashboard, because the web and bot services share the same allowance.

## Local development

`docker compose up` still runs the `reminders` worker, which polls every
`NOTIFICATIONS_POLL_INTERVAL_SECONDS`. To try the endpoint locally:

```bash
curl -X POST http://localhost:8000/v1/internal/reminders/tick \
  -H "Authorization: Bearer $REMINDERS_CRON_SECRET"
```
