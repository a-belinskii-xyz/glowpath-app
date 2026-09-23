import pytest
from app.config import Settings
from app.db.postgres_url import normalize_postgres_url


def test_rewrites_neon_url_to_psycopg3() -> None:
    url = (
        "postgresql://user:secret@ep-example.eu-central-1.aws.neon.tech/glowpath_db?sslmode=require"
    )
    assert normalize_postgres_url(url) == (
        "postgresql+psycopg://user:secret@ep-example.eu-central-1.aws.neon.tech/"
        "glowpath_db?sslmode=require"
    )


def test_rewrites_postgres_scheme_and_psycopg2() -> None:
    assert normalize_postgres_url("postgres://mood:mood@localhost/mood_tracker") == (
        "postgresql+psycopg://mood:mood@localhost/mood_tracker"
    )
    assert normalize_postgres_url("postgresql+psycopg2://mood:mood@localhost/mood_tracker") == (
        "postgresql+psycopg://mood:mood@localhost/mood_tracker"
    )


def test_settings_use_psycopg_and_prefer_unpooled_for_migrations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:secret@ep-example-pooler.eu-central-1.aws.neon.tech/glowpath_db?sslmode=require",
    )
    monkeypatch.setenv(
        "DATABASE_URL_UNPOOLED",
        "postgres://user:secret@ep-example.eu-central-1.aws.neon.tech/glowpath_db?sslmode=require",
    )
    loaded = Settings()
    assert loaded.database_url.startswith("postgresql+psycopg://")
    assert "-pooler" in loaded.database_url
    assert loaded.migration_database_url.startswith("postgresql+psycopg://")
    assert "-pooler" not in loaded.migration_database_url


def test_leaves_psycopg3_url_and_strips_quotes() -> None:
    url = "postgresql+psycopg://mood:mood@localhost/mood_tracker"
    assert normalize_postgres_url(url) == url
    assert normalize_postgres_url(f'"{url}"') == url
    assert normalize_postgres_url("") == ""
