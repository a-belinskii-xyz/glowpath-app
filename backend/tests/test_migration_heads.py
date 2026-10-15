from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_migrations_have_single_head_and_unique_ids() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    script = ScriptDirectory.from_config(config)

    revisions = [
        line.split("=", 1)[1].strip().strip('"')
        for path in (BACKEND_DIR / "alembic" / "versions").glob("*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("revision: str =")
    ]
    assert len(revisions) == len(set(revisions)), "two migrations share a revision id"
    assert len(script.get_heads()) == 1, "migrations have more than one head"
