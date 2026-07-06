import pytest
from alembic.config import Config
from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from tests.migrations import make_alembic_config


def _database_available() -> bool:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
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
    if not _database_available():
        pytest.skip("PostgreSQL is not available for migration tests")
    return make_alembic_config(settings.database_url)
