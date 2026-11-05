"""Root conftest: runs before tests/conftest.py imports the app."""

import os

# backend/.env may hold a real SENTRY_DSN; test failures must not reach Sentry.
os.environ["SENTRY_DSN"] = ""
