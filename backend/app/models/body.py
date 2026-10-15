import uuid
from datetime import date, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name


class Measurement(TimestampMixin, Base):
    """A number measured on a local day, such as body weight (GP-47). One per kind per day."""

    __tablename__ = table_name("measurements")
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "day"),
        CheckConstraint("kind IN ('weight')", name="measurement_kind_values"),
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
    kind: Mapped[str] = mapped_column(String(16))
    day: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(5, 1))


class FoodLog(TimestampMixin, Base):
    """One line of what was eaten on a local day, with no calories or judgement (GP-47)."""

    __tablename__ = table_name("food_logs")
    __table_args__ = (
        CheckConstraint(
            "meal IS NULL OR meal IN ('morning', 'day', 'evening', 'snack')",
            name="food_log_meal_values",
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
    day: Mapped[date] = mapped_column(Date)
    meal: Mapped[str | None] = mapped_column(String(16), nullable=True)
    text: Mapped[str] = mapped_column(String(500))


class BodySettings(TimestampMixin, Base):
    """Which body blocks show on «Моё»; both are off until the person turns them on."""

    __tablename__ = table_name("body_settings")

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="CASCADE"),
        primary_key=True,
    )
    show_weight: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    show_food: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # Blur the weight number on «Моё» until tapped.
    hide_weight: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    show_sleep: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # Only for BMI next to the weight; nothing is shown without it (GP-48).
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)


class BodyFoodGoal(Base):
    """A goal the food drawer offers to mark, e.g. "Eat properly"; up to three per person."""

    __tablename__ = table_name("body_food_goals")

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="CASCADE"),
        primary_key=True,
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("goals"), ondelete="CASCADE"),
        primary_key=True,
    )
    # Which of the three slots in settings holds this goal.
    position: Mapped[int] = mapped_column(Integer, server_default="0")


class SleepLog(TimestampMixin, Base):
    """One night, filed under the day of waking up (GP-48). Times are local clock times."""

    __tablename__ = table_name("sleep_logs")
    __table_args__ = (
        UniqueConstraint("user_id", "day"),
        CheckConstraint(
            "quality IS NULL OR quality IN ('hard', 'ok', 'good')",
            name="sleep_log_quality_values",
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
    day: Mapped[date] = mapped_column(Date)
    bed_time: Mapped[time] = mapped_column(Time)
    wake_time: Mapped[time] = mapped_column(Time)
    # When actually out of bed; null means right after waking.
    up_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    quality: Mapped[str | None] = mapped_column(String(8), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
