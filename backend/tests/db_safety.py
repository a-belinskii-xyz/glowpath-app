"""Guards against running destructive test operations on non-test databases."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from app.config import settings

# Application databases that must never be used for destructive migration tests.
PROTECTED_DATABASE_NAMES: frozenset[str] = frozenset({"mood_tracker"})

_TEST_DATABASE_SUFFIX = "_test"
_PRODUCTION_ENV_VALUES = frozenset({"production", "prod"})


def parse_database_name(database_url: str) -> str:
    normalized = re.sub(r"\+[^:]+", "", database_url, count=1)
    parsed = urlparse(normalized)
    name = parsed.path.lstrip("/").split("?")[0]
    if not name:
        msg = f"Could not parse database name from URL: {database_url!r}"
        raise ValueError(msg)
    return name


def get_test_database_url() -> str:
    return settings.test_database_url


def assert_safe_test_database(database_url: str) -> None:
    """Refuse to run destructive tests unless the target is clearly a test database."""
    app_env = os.environ.get("MOOD_TRACKER_ENV", os.environ.get("APP_ENV", "")).lower()
    if app_env in _PRODUCTION_ENV_VALUES:
        raise RuntimeError("Refusing to run tests when APP_ENV/MOOD_TRACKER_ENV is production.")

    if database_url.rstrip("/") == settings.database_url.rstrip("/"):
        raise RuntimeError(
            "TEST_DATABASE_URL must differ from DATABASE_URL. "
            "Point tests at a dedicated database (e.g. mood_tracker_test)."
        )

    db_name = parse_database_name(database_url)

    if db_name in PROTECTED_DATABASE_NAMES:
        raise RuntimeError(
            f"Refusing to run tests against protected database {db_name!r}. "
            "Configure TEST_DATABASE_URL to a dedicated test database "
            "(e.g. mood_tracker_test)."
        )

    if not db_name.endswith(_TEST_DATABASE_SUFFIX):
        raise RuntimeError(
            f"Refusing to run tests against {db_name!r}: "
            f"test database name must end with {_TEST_DATABASE_SUFFIX!r}."
        )
