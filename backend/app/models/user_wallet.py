import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.user import User


class UserWallet(TimestampMixin, Base):
    __tablename__ = table_name("user_wallets")
    __table_args__ = (CheckConstraint("balance >= 0", name="user_wallet_balance_non_negative"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="CASCADE"),
        primary_key=True,
    )
    balance: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))

    user: Mapped["User"] = relationship(back_populates="wallet")
