from pathlib import Path

from alembic.config import Config

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def make_alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url)
    return config
