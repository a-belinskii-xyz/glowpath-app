"""Staff metrics (GP-21, GP-68): where accounts come from and who keeps writing.

Staff accounts are left out. Activity counts distinct local days on which a user
wrote entries (by ``created_at`` in the user's timezone); restored entries are skipped.
A user is *active* in a week with entries on 1+ local day and *regular* with entries on
``REGULAR_MIN_DAYS``+ distinct local days: two taps on the same day are not a return.

Retention cohorts (GP-68) group users by signup week (Monday 00:00 to Sunday 24:00 UTC,
by ``User.created_at``) and by signup source (``unknown`` when missing). Week Wk is
counted from each user's own signup: W1 is ``[created_at, created_at + 7 days)``, W2 the
next seven days, up to W4. A user enters the denominator of Wk only once Wk has ended;
a cell no one has reached yet is ``None`` (shown as a dash), not 0 %.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session

from app.models.mood_entry import MoodEntry
from app.models.user import User

UNKNOWN_SIGNUP_SOURCE = "unknown"
REGULAR_MIN_DAYS = 2
WEEKS_SHOWN = 4
COHORT_WEEKS = 8
RETENTION_WEEKS = 4
_WEEK = timedelta(days=7)


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
class Retention:
    """How many of ``size`` users wrote in each week W1–W4 after their signup.

    ``eligible[k]`` users have lived through week k+1. ``active`` and ``regular`` count
    among them and are ``None`` while ``eligible[k]`` is 0.
    """

    size: int
    eligible: tuple[int, ...]
    active: tuple[int | None, ...]
    regular: tuple[int | None, ...]


@dataclass(frozen=True, slots=True)
class SourceCohort:
    source: str
    retention: Retention


@dataclass(frozen=True, slots=True)
class WeekCohort:
    week_start: datetime
    retention: Retention  # every source of the week together
    sources: list[SourceCohort]


@dataclass(frozen=True, slots=True)
class MetricsReport:
    generated_at: datetime
    sources: list[SourceCount]
    weeks: list[WeekStats]
    cohorts: list[WeekCohort]
    cohort_total: Retention


def build_metrics_report(db: Session, *, now: datetime | None = None) -> MetricsReport:
    now = now or datetime.now(UTC)
    cohorts, cohort_total = _retention_cohorts(db, now=now)
    return MetricsReport(
        generated_at=now,
        sources=_signup_sources(db, now=now),
        weeks=[
            _week_stats(
                db, starts_at=now - timedelta(days=7 * (i + 1)), ends_at=now - timedelta(days=7 * i)
            )
            for i in range(WEEKS_SHOWN)
        ],
        cohorts=cohorts,
        cohort_total=cohort_total,
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


@dataclass(slots=True)
class _Tally:
    size: int = 0
    eligible: list[int] = field(default_factory=lambda: [0] * RETENTION_WEEKS)
    active: list[int] = field(default_factory=lambda: [0] * RETENTION_WEEKS)
    regular: list[int] = field(default_factory=lambda: [0] * RETENTION_WEEKS)

    def add(self, *, weeks_lived: int, days: Sequence[int]) -> None:
        self.size += 1
        for k in range(weeks_lived):
            self.eligible[k] += 1
            self.active[k] += int(days[k] >= 1)
            self.regular[k] += int(days[k] >= REGULAR_MIN_DAYS)

    def freeze(self) -> Retention:
        def counted(values: list[int]) -> tuple[int | None, ...]:
            return tuple(n if e else None for n, e in zip(values, self.eligible, strict=True))

        return Retention(
            size=self.size,
            eligible=tuple(self.eligible),
            active=counted(self.active),
            regular=counted(self.regular),
        )


def utc_week_start(moment: datetime) -> datetime:
    """Monday 00:00 UTC of the week that holds ``moment``."""
    day = moment.astimezone(UTC).date()
    return datetime.combine(day - timedelta(days=day.weekday()), time(), tzinfo=UTC)


def _retention_cohorts(
    db: Session, *, now: datetime, weeks: int = COHORT_WEEKS
) -> tuple[list[WeekCohort], Retention]:
    """Signup cohorts of the last ``weeks`` UTC weeks, newest first, and their total.

    Two queries: the users of the window, then distinct local days with entries per
    user and week since signup.
    """
    first_week = utc_week_start(now) - _WEEK * (weeks - 1)
    in_window = (
        User.is_staff.is_(False),
        User.created_at >= first_week,
        User.created_at <= now,
    )
    users = db.execute(
        select(
            User.id,
            User.created_at,
            func.coalesce(User.signup_source, UNKNOWN_SIGNUP_SOURCE),
        ).where(*in_window)
    ).all()

    week_no = case(
        *(
            (MoodEntry.created_at < User.created_at + _WEEK * k, k)
            for k in range(1, RETENTION_WEEKS + 1)
        )
    )
    local_day = func.date(func.timezone(User.timezone, MoodEntry.created_at))
    written = (
        select(MoodEntry.user_id, week_no.label("week_no"), local_day.label("day"))
        .select_from(MoodEntry)
        .join(User, User.id == MoodEntry.user_id)
        .where(
            *in_window,
            MoodEntry.restore_id.is_(None),
            MoodEntry.created_at >= User.created_at,
            MoodEntry.created_at < User.created_at + _WEEK * RETENTION_WEEKS,
        )
        .distinct()
        .subquery()
    )
    days: dict[tuple[uuid.UUID, int], int] = {
        (user_id, week): count
        for user_id, week, count in db.execute(
            select(written.c.user_id, written.c.week_no, func.count()).group_by(
                written.c.user_id, written.c.week_no
            )
        ).all()
    }

    by_source: defaultdict[datetime, defaultdict[str, _Tally]] = defaultdict(
        lambda: defaultdict(_Tally)
    )
    by_week: defaultdict[datetime, _Tally] = defaultdict(_Tally)
    total = _Tally()
    for user_id, created_at, source in users:
        weeks_lived = min(RETENTION_WEEKS, (now - created_at) // _WEEK)
        week_days = [days.get((user_id, k), 0) for k in range(1, RETENTION_WEEKS + 1)]
        week = utc_week_start(created_at)
        for tally in (by_source[week][source], by_week[week], total):
            tally.add(weeks_lived=weeks_lived, days=week_days)

    cohorts = [
        WeekCohort(
            week_start=week,
            retention=by_week[week].freeze(),
            sources=[
                SourceCohort(source=name, retention=tally.freeze())
                for name, tally in sorted(
                    by_source[week].items(), key=lambda item: (-item[1].size, item[0])
                )
            ],
        )
        for week in sorted(by_week, reverse=True)
    ]
    return cohorts, total.freeze()
