import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, index_name, table_name


class DiaryRestoreStatus(StrEnum):
    PREVIEW = "preview"
    APPLIED = "applied"
    CANCELLED = "cancelled"


class DiaryRestore(TimestampMixin, Base):
    """One attempt to restore a diary from an export archive (GP-20).

    ``preview`` holds the parsed archive and the uploaded files in temporary storage
    until the user confirms or cancels. Rows created by an applied restore point back
    here through their ``restore_id``.
    """

    __tablename__ = table_name("diary_restores")
    __table_args__ = (
        CheckConstraint(
            "status IN ('preview', 'applied', 'cancelled')",
            name="diary_restore_status_values",
        ),
        Index(index_name("diary_restores", "user_id__status"), "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    format_version: Mapped[int] = mapped_column(Integer, nullable=False)
    archive_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Parsed archive at the current format version; cleared once applied or cancelled.
    archive: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Path inside the archive -> temporary storage key, while in preview.
    stored_files: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
