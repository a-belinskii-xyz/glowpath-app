"""Staff metrics (GP-21): where accounts come from and who keeps writing.

Staff accounts are left out. Activity counts distinct local days on which a user
wrote entries (by ``created_at`` in the user's timezone); restored entries are skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session

from app.models.mood_entry import MoodEntry
from app.models.user import User

UNKNOWN_SIGNUP_SOURCE = "unknown"
REGULAR_MIN_DAYS = 3
WEEKS_SHOWN = 4


@dataclass(frozen=True, slots=True)
class SourceCount:
    source: str
    last_7_days: int
    last_30_days: int
    total: int


@dataclass(frozen=True, slots=True)
class WeekStats:
    starts_at: datetime
    ends_at: datetime
    signups: int
    active: int
    regular: int


@dataclass(frozen=True, slots=True)
class MetricsReport:
    generated_at: datetime
    sources: list[SourceCount]
    weeks: list[WeekStats]


def build_metrics_report(db: Session, *, now: datetime | None = None) -> MetricsReport:
    now = now or datetime.now(UTC)
    return MetricsReport(
        generated_at=now,
        sources=_signup_sources(db, now=now),
        weeks=[
            _week_stats(
                db, starts_at=now - timedelta(days=7 * (i + 1)), ends_at=now - timedelta(days=7 * i)
            )
            for i in range(WEEKS_SHOWN)
        ],
    )


def _signup_sources(db: Session, *, now: datetime) -> list[SourceCount]:
    source = func.coalesce(User.signup_source, UNKNOWN_SIGNUP_SOURCE)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    rows = db.execute(
        select(
            source,
            func.count(case((User.created_at >= week_ago, 1))),
            func.count(case((User.created_at >= month_ago, 1))),
            func.count(),
        )
        .where(User.is_staff.is_(False))
        .group_by(source)
        .order_by(func.count().desc(), source)
    ).all()
    return [
        SourceCount(source=name, last_7_days=week, last_30_days=month, total=total)
        for name, week, month, total in rows
    ]


def _week_stats(db: Session, *, starts_at: datetime, ends_at: datetime) -> WeekStats:
    signups = db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.is_staff.is_(False),
            User.created_at >= starts_at,
            User.created_at < ends_at,
        )
    )
    local_day = func.date(func.timezone(User.timezone, MoodEntry.created_at))
    days_per_user = (
        select(func.count(distinct(local_day)).label("days"))
        .select_from(MoodEntry)
        .join(User, User.id == MoodEntry.user_id)
        .where(
            User.is_staff.is_(False),
            MoodEntry.restore_id.is_(None),
            MoodEntry.created_at >= starts_at,
            MoodEntry.created_at < ends_at,
        )
        .group_by(MoodEntry.user_id)
        .subquery()
    )
    active, regular = db.execute(
        select(
            func.count(),
            func.count(case((days_per_user.c.days >= REGULAR_MIN_DAYS, 1))),
        ).select_from(days_per_user)
    ).one()
    return WeekStats(
        starts_at=starts_at,
        ends_at=ends_at,
        signups=signups or 0,
        active=active,
        regular=regular,
    )
