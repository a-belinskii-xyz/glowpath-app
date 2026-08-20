import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, index_name, table_name

if TYPE_CHECKING:
    from app.models.icon_pack import IconPack
    from app.models.user import User


class WalletLedger(TimestampMixin, Base):
    __tablename__ = table_name("wallet_ledger")
    __table_args__ = (
        CheckConstraint(
            "kind IN ('grant', 'unlock_pack', 'adjustment', 'refund')",
            name="wallet_ledger_kind_values",
        ),
        Index(
            index_name("wallet_ledger", "user_created"),
            "user_id",
            text("created_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="CASCADE"),
        index=True,
    )
    delta: Mapped[int] = mapped_column(BigInteger)
    balance_after: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(32))
    pack_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("icon_packs"), ondelete="SET NULL"),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    pack: Mapped["IconPack | None"] = relationship()
    creator: Mapped["User | None"] = relationship(foreign_keys=[created_by])
