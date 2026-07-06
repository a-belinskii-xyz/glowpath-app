"""Stairway test: upgrade → downgrade → upgrade for each migration revision."""

import pytest
from alembic.command import downgrade, upgrade
from alembic.config import Config
from alembic.script import Script, ScriptDirectory

from tests.migrations import make_alembic_config


def _get_revisions() -> list[Script]:
    config = make_alembic_config("postgresql+psycopg://")
    revisions_dir = ScriptDirectory.from_config(config)
    revisions = list(revisions_dir.walk_revisions("base", "heads"))
    revisions.reverse()
    return revisions


@pytest.mark.parametrize("revision", _get_revisions(), ids=lambda r: r.revision)
def test_migrations_stairway(alembic_config: Config, revision: Script) -> None:
    downgrade(alembic_config, revision.down_revision or "base")
    upgrade(alembic_config, revision.revision)
    downgrade(alembic_config, revision.down_revision or "-1")
    upgrade(alembic_config, revision.revision)
