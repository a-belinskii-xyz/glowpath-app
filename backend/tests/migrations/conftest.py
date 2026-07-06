import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from tests.db_safety import assert_safe_test_database, get_test_database_url
from tests.migrations import make_alembic_config

TEST_DATABASE_URL = get_test_database_url()


def _database_available() -> bool:
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        return False
    finally:
        engine.dispose()
    return True


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    assert_safe_test_database(TEST_DATABASE_URL)
    if not _database_available():
        pytest.skip("PostgreSQL is not available for migration tests")
    return make_alembic_config(TEST_DATABASE_URL)
