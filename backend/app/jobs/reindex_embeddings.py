"""CLI: reindex mood-entry embeddings for semantic search.

Usage (from backend/ with venv active, or via make):

    python -m app.jobs.reindex_embeddings
"""

from __future__ import annotations

import logging
import sys

from app.db.session import SessionLocal
from app.services.embedding_service import reindex_all_embeddings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    db = SessionLocal()
    try:
        updated = reindex_all_embeddings(db)
        logger.info("Reindexed %s mood entries", updated)
        return 0
    except Exception:
        logger.exception("Failed to reindex embeddings")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
