"""Normalize Postgres URLs onto the psycopg 3 SQLAlchemy driver.

Neon and Render hand out ``postgresql://`` or ``postgres://``. SQLAlchemy maps
those schemes to psycopg2, which this project does not install. pgvector is
registered through ``pgvector.psycopg`` (psycopg 3), so the driver in the URL
has to match.
"""

from __future__ import annotations

_PSYCOPG_SCHEME = "postgresql+psycopg://"
_PLAIN_SCHEMES = ("postgresql://", "postgres://", "postgresql+psycopg2://")


def normalize_postgres_url(url: str) -> str:
    """Rewrite libpq-style URLs so SQLAlchemy loads psycopg 3."""
    value = url.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    if not value or value.startswith(_PSYCOPG_SCHEME):
        return value
    for scheme in _PLAIN_SCHEMES:
        if value.startswith(scheme):
            return _PSYCOPG_SCHEME + value[len(scheme) :]
    return value
