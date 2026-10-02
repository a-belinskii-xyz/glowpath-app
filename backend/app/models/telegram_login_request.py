import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.names import table_name


class TelegramLoginRequest(Base):
    """Website sign-in confirmed in the bot via ``/start login_<code>``.

    The browser keeps ``poll_token`` and exchanges it for tokens once the bot has
    confirmed the code with the Telegram account that pressed Start.
    """

    __tablename__ = table_name("telegram_login_requests")

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    poll_hash: Mapped[str] = mapped_column(String(64), unique=True)
    timezone: Mapped[str] = mapped_column(String(64))
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    signup_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    telegram_locale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
