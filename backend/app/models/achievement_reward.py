import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.achievement import Achievement
    from app.models.catalog_icon import CatalogIcon
    from app.models.icon_pack import IconPack


class AchievementReward(TimestampMixin, Base):
    __tablename__ = table_name("achievement_rewards")
    __table_args__ = (
        CheckConstraint(
            "kind IN ('tokens', 'icon_pack', 'catalog_icon')",
            name="achievement_reward_kind_values",
        ),
        CheckConstraint(
            "("
            "kind = 'tokens' AND amount IS NOT NULL AND amount > 0 "
            "AND pack_id IS NULL AND catalog_icon_id IS NULL"
            ") OR ("
            "kind = 'icon_pack' AND pack_id IS NOT NULL AND amount IS NULL "
            "AND catalog_icon_id IS NULL"
            ") OR ("
            "kind = 'catalog_icon' AND catalog_icon_id IS NOT NULL "
            "AND amount IS NULL AND pack_id IS NULL"
            ")",
            name="achievement_reward_fields",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    achievement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("achievements"), ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pack_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("icon_packs"), ondelete="SET NULL"),
        nullable=True,
    )
    catalog_icon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("catalog_icons"), ondelete="SET NULL"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    achievement: Mapped["Achievement"] = relationship(back_populates="rewards")
    pack: Mapped["IconPack | None"] = relationship()
    catalog_icon: Mapped["CatalogIcon | None"] = relationship()
