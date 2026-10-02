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

## Moving the guest diary into an account (import)

Guest data is merged into the server when:

1. The guest signs in from the same browser (Telegram bot sign-in, Telegram Login, Google, email), **and**
2. `visitor_id` from the guest session is stored on the user as `pending_guest_device_id`, **and**
3. The frontend calls `POST /v1/guest/import` with the IndexedDB payload.

Backend guard in `import_guest_diary`:

```text
user.pending_guest_device_id != visitor_id   → 409 guest_import_not_allowed
user.guest_imported_at is set                → { skipped: true } (already imported from this browser)
otherwise                                    → import
```

`pending_guest_device_id` is set:

- when a **new** account is created with a `visitor_id` (`_link_pending_guest_device`);
- on sign-in to an **existing** account with a `visitor_id` (`_link_guest_device_on_existing_login`).
  A different `visitor_id` than the stored one also resets `guest_imported_at`, so each browser can be imported once.

The Mini App never sends a `visitor_id` and has no guest mode: it can't see entries kept in a browser.

### New account

Import runs right after sign-in, without asking. The account takes the guest's mood preferences and onboarding state.

### Existing account

The frontend asks first (`GuestImportPrompt`): what moves (entries with mood, notes, tags and goals; tags, goals and note
templates missing from the account) and that nothing in the account is replaced. On “Not now” the entries stay in the
browser and the question comes back at the next sign-in. When the account already has entries, it keeps its own mood
preferences and onboarding state; tags, goals and templates are merged by slug.

`mt_guest_devices.last_auth_event`:

| `last_auth_event` | Meaning |
|-------------------|---------|
| `imported` | Guest diary was merged into the account |
| `existing_login_skipped` | User signed into an existing account and has not moved the entries (yet) |
| `none` | No auth event yet |

Staff summary: `GET /v1/guest/experiment/summary` exposes `treatment_converted` (any conversion) and `treatment_existing_login_skipped`.

After a successful import IndexedDB is cleared. Imported entries don't count toward the streak: the server counts only
entries written on the day they record, and the payload has no write time.

## Frontend notes

- `completeLogin` imports for a new account and sets `pendingGuestImport` for an existing one.
- The guest banner invites signing in with Telegram and lists what an account gives; the login page hides
  “Open in Telegram” for guests, since the Mini App can't see the browser's entries.
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
| Import after auth | `frontend/src/lib/guestImport.ts`, `frontend/src/components/GuestImportPrompt.tsx` |

## Tests

- `backend/tests/test_guest_import.py` — import after registration, into an existing account after sign-in (email and Telegram)
- `backend/tests/test_guest_experiment_api.py` — bootstrap, heartbeat
- `backend/tests/test_guest_experiment_flags.py` — rollout bucketing
