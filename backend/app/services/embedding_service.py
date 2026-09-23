"""Local text embeddings via fastembed for semantic mood-entry search."""

from __future__ import annotations

import logging
import math
import threading
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core.markdown_plain_text import markdown_to_plain_text
from app.models.mood_entry import MoodEntry

if TYPE_CHECKING:
    from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

_model_lock = threading.Lock()
_model: TextEmbedding | None = None


def build_entry_search_text(entry: MoodEntry) -> str | None:
    """Build searchable plain text from note + attachment transcriptions."""
    parts: list[str] = []
    if entry.note:
        plain = markdown_to_plain_text(entry.note).strip()
        if plain:
            parts.append(plain)
    for attachment in entry.attachments:
        transcription = (attachment.transcription or "").strip()
        if transcription:
            parts.append(transcription)
    if not parts:
        return None
    return "\n".join(parts)


def _get_model() -> TextEmbedding:
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from fastembed import TextEmbedding

        logger.info("Loading embedding model %s", settings.embedding_model)
        _model = TextEmbedding(model_name=settings.embedding_model)
        return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed one or more texts. Returns L2-normalized vectors of ``embedding_dims``."""
    if not texts:
        return []
    if not settings.embedding_enabled:
        raise RuntimeError("Embeddings are disabled (EMBEDDING_ENABLED=false)")

    model = _get_model()
    vectors = list(model.embed(texts))
    result: list[list[float]] = []
    for vector in vectors:
        values = [float(x) for x in vector]
        if len(values) != settings.embedding_dims:
            raise RuntimeError(
                f"Embedding dim mismatch: got {len(values)}, expected {settings.embedding_dims}"
            )
        result.append(values)
    return result


def upsert_entry_embedding(db: Session, entry: MoodEntry) -> None:
    """Compute and assign ``entry.embedding`` (or clear it). Does not commit."""
    if not settings.embedding_enabled:
        return

    text = build_entry_search_text(entry)
    if text is None:
        entry.embedding = None
        return

    entry.embedding = embed_texts([text])[0]
    db.add(entry)


def reindex_all_embeddings(db: Session, *, batch_size: int = 32) -> int:
    """Recompute embeddings for all entries that have searchable text. Returns count updated."""
    from sqlalchemy import select

    stmt = select(MoodEntry).options(selectinload(MoodEntry.attachments)).order_by(MoodEntry.id)
    entries = list(db.scalars(stmt).all())
    updated = 0
    batch_entries: list[MoodEntry] = []
    batch_texts: list[str] = []

    def flush_batch() -> None:
        nonlocal updated
        if not batch_texts:
            return
        vectors = embed_texts(batch_texts)
        for entry, vector in zip(batch_entries, vectors, strict=True):
            entry.embedding = vector
            db.add(entry)
            updated += 1
        batch_entries.clear()
        batch_texts.clear()

    for entry in entries:
        text = build_entry_search_text(entry)
        if text is None:
            if entry.embedding is not None:
                entry.embedding = None
                db.add(entry)
                updated += 1
            continue
        batch_entries.append(entry)
        batch_texts.append(text)
        if len(batch_texts) >= batch_size:
            flush_batch()
            db.commit()

    flush_batch()
    db.commit()
    return updated


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Utility for tests / debugging."""
    if len(a) != len(b):
        raise ValueError("vector length mismatch")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
