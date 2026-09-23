"""Resolve which database URL Alembic should use."""


def resolve_alembic_database_url(*, configured_url: str | None, settings_url: str) -> str:
    """Prefer an explicit Config URL; fall back to app settings.

    Alembic.ini ships a placeholder ``driver://...`` URL. Migration tests set a
    real URL on the Config before invoking Alembic — that must win, otherwise
    stairway downgrades wipe the application database.
    """
    configured = (configured_url or "").strip()
    if configured and not configured.startswith("driver://"):
        return configured
    return settings_url
