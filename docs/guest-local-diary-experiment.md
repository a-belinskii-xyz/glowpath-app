# Guest local diary experiment

Optional product experiment: visitors in the **treatment** cohort can use the app without registering. Data lives in the browser (IndexedDB) until the user creates a **new** account.

Controlled by backend env vars:

| Variable | Meaning |
|----------|---------|
| `FEATURE_GUEST_LOCAL_DIARY` | Kill switch (`true` / `false`) |
| `FEATURE_GUEST_LOCAL_DIARY_PERCENT` | Rollout 0–100 (stable bucket per `visitor_id`) |
| `FEATURE_GUEST_LOCAL_DIARY_VISITOR_IDS` | Comma-separated UUID allowlist (always control when flag is off) |

## Assignment

1. Frontend calls `POST /v1/features/bootstrap` with a device fingerprint.
2. Server creates or reuses a row in `mt_visitors`, sets cookie `mt_vid`, returns `guest_local_diary: true|false`.
3. Treatment visitors get the full diary shell (entries, tags, goals, tracker settings) with registration-gated features shown but disabled in the UI.

Telemetry: `POST /v1/guest/heartbeat` (entry count, onboarding flag, timezone, locale) → `mt_guest_devices`.

## What guests can and cannot do

| Allowed locally | Requires registration |
|-----------------|----------------------|
| Mood entries (no photos/voice) | Photo & audio attachments |
| Default + emoji tag/goal icons | Custom uploaded / marketplace icons |
| Tags, goals, templates, mood prefs | Gallery, market, achievements, profile account features |
| Calendar, stats, streak (client-side) | Pattern insights (server ML) |
| Onboarding suggestions (public API) | Email, Telegram, reminders |

## Sync on registration (import)

Guest data is merged into the server **only** when:

1. User **registers** a new account (email) or signs in with Google and a **new** user row is created, **and**
2. `visitor_id` from the guest session was stored on the user as `pending_guest_device_id`, **and**
3. After login, frontend calls `POST /v1/guest/import` with the IndexedDB payload.

Backend guard in `import_guest_diary`:

```text
user.pending_guest_device_id == visitor_id   → import allowed
otherwise                                    → 409 guest_import_not_allowed
```

`pending_guest_device_id` is set only in:

- `register_user` (email signup)
- `authenticate_google_profile` when a **new** Google user is created

It is **not** set on login to an existing account.

### Existing account login (`existing_login_skipped`)

When a treatment guest logs into an **existing** account (email+password or Google account already in DB):

1. Backend calls `mark_visitor_converted(..., auth_event=existing_login_skipped)`.
2. **`pending_guest_device_id` is not set** — import API returns 409.
3. Local guest diary **stays in the browser**; frontend shows a warning on the login page.
4. IndexedDB is **not** cleared.

Important: analytics fields `converted_user_id` / `converted_at` on `mt_visitors` and `mt_guest_devices` are still filled. That means the visitor is counted as “converted” in experiment summaries even though **no data was imported**. Check `mt_guest_devices.last_auth_event`:

| `last_auth_event` | Meaning |
|-------------------|---------|
| `imported` | Guest diary was merged into the account (`guest_imported_at` set on user) |
| `existing_login_skipped` | User signed into an existing account; local data intentionally not merged |
| `none` | No auth event yet |

Staff summary: `GET /v1/guest/experiment/summary` exposes `treatment_converted` (any conversion) and `treatment_existing_login_skipped` (existing-login path only).

### Email registration flow

1. Guest → Register (with `visitor_id`) → `pending_guest_device_id` linked.
2. Verify email → Login → import runs on first authenticated import call.
3. On success: `guest_imported_at` set, `last_auth_event = imported`, IndexedDB cleared.

Repeat import returns `{ skipped: true }`.

## Frontend notes

- `tryImportGuestDiaryAfterAuth` runs after every login; backend rejects import for existing accounts (errors are swallowed; local data kept).
- Guest entry count in the top banner is driven by `subscribeGuestEntryCount` (updates when local entries change, not only on page load).

## Related code

| Area | Path |
|------|------|
| Feature flag | `backend/app/core/feature_flags.py` |
| Bootstrap | `backend/app/api/v1/features.py` |
| Auth linking | `backend/app/services/auth_service.py` |
| Import | `backend/app/services/guest_import_service.py` |
| Experiment telemetry | `backend/app/services/visitor_experiment_service.py` |
| IndexedDB store | `frontend/src/guest/store.ts` |
| Import after auth | `frontend/src/lib/guestImport.ts` |

## Tests

- `backend/tests/test_guest_import.py` — import allowed after registration; rejected after existing login
- `backend/tests/test_guest_experiment_api.py` — bootstrap, heartbeat
- `backend/tests/test_guest_experiment_flags.py` — rollout bucketing
