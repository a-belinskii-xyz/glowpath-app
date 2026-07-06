import pytest

from tests.db_safety import (
    PROTECTED_DATABASE_NAMES,
    assert_safe_test_database,
    parse_database_name,
)


def test_parse_database_name() -> None:
    assert (
        parse_database_name("postgresql+psycopg://mood:mood@localhost:5432/mood_tracker_test")
        == "mood_tracker_test"
    )


def test_assert_safe_test_database_accepts_test_db() -> None:
    assert_safe_test_database("postgresql+psycopg://mood:mood@localhost:5432/mood_tracker_test")


@pytest.mark.parametrize("database_name", sorted(PROTECTED_DATABASE_NAMES))
def test_assert_safe_test_database_rejects_protected_db(
    database_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tests.db_safety.settings.database_url",
        "postgresql+psycopg://mood:mood@localhost:5432/other_app",
    )
    url = f"postgresql+psycopg://mood:mood@localhost:5432/{database_name}"
    with pytest.raises(RuntimeError, match="protected database"):
        assert_safe_test_database(url)


def test_assert_safe_test_database_rejects_non_test_suffix() -> None:
    with pytest.raises(RuntimeError, match="must end with '_test'"):
        assert_safe_test_database(
            "postgresql+psycopg://mood:mood@localhost:5432/mood_tracker_staging"
        )
