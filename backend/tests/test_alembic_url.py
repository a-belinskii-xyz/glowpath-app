from app.db.alembic_url import resolve_alembic_database_url


def test_resolve_prefers_explicit_config_url() -> None:
    settings_url = "postgresql+psycopg://mood:mood@localhost:5437/mood_tracker"
    configured = "postgresql+psycopg://mood:mood@localhost:5437/mood_tracker_test"
    assert (
        resolve_alembic_database_url(configured_url=configured, settings_url=settings_url)
        == configured
    )


def test_resolve_falls_back_from_alembic_placeholder() -> None:
    settings_url = "postgresql+psycopg://mood:mood@localhost:5437/mood_tracker"
    assert (
        resolve_alembic_database_url(
            configured_url="driver://user:pass@localhost/dbname",
            settings_url=settings_url,
        )
        == settings_url
    )


def test_resolve_falls_back_from_empty_url() -> None:
    settings_url = "postgresql+psycopg://mood:mood@localhost:5437/mood_tracker"
    assert (
        resolve_alembic_database_url(configured_url=None, settings_url=settings_url) == settings_url
    )
    assert (
        resolve_alembic_database_url(configured_url="  ", settings_url=settings_url) == settings_url
    )
