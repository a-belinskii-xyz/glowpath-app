"""Retention cohorts in staff metrics (GP-68)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.diary_restore import DiaryRestore
from app.models.mood_entry import MoodEntry
from app.models.user import User
from app.services.metrics_service import (
    COHORT_WEEKS,
    Retention,
    WeekCohort,
    build_metrics_report,
    utc_week_start,
)
from sqlalchemy.orm import Session

# A fixed clock far from the real one, so rows other tests create "now" stay out of the window.
MONDAY = datetime(2031, 3, 3, tzinfo=UTC)
NOW = MONDAY + timedelta(days=2, hours=12)  # Wednesday 12:00 UTC
WEEK = timedelta(days=7)


def _user(
    db: Session,
    *,
    created_at: datetime,
    source: str | None = None,
    tz: str = "UTC",
    staff: bool = False,
) -> User:
    user = User(
        email=f"cohort-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone=tz,
        signup_source=source,
        is_staff=staff,
        created_at=created_at,
    )
    db.add(user)
    db.flush()
    return user


def _entry(db: Session, user: User, at: datetime, *, restore_id: uuid.UUID | None = None) -> None:
    db.add(
        MoodEntry(
            user_id=user.id,
            recorded_at=at,
            created_at=at,
            score=3,
            score_color="#22c55e",
            restore_id=restore_id,
        )
    )


def _report(db: Session) -> tuple[list[WeekCohort], Retention]:
    db.flush()
    report = build_metrics_report(db, now=NOW)
    return report.cohorts, report.cohort_total


def _by_source(cohorts: list[WeekCohort]) -> dict[str, Retention]:
    return {row.source: row.retention for cohort in cohorts for row in cohort.sources}


def test_cohorts_group_signup_weeks_and_sources(db: Session) -> None:
    old_week = MONDAY - 5 * WEEK
    alice = _user(db, created_at=old_week + timedelta(hours=1), source="alice")
    bob = _user(db, created_at=old_week + timedelta(days=2), source="bob")
    newer = _user(db, created_at=NOW - (2 * WEEK + timedelta(days=1)))
    staff = _user(db, created_at=old_week + timedelta(hours=3), source="alice", staff=True)

    def at(user: User, week: int, day: int) -> datetime:
        return user.created_at + (week - 1) * WEEK + timedelta(days=day, hours=1)

    for week, day in [(1, 0), (1, 3), (2, 1), (4, 2), (4, 5)]:
        _entry(db, alice, at(alice, week, day))
    _entry(db, bob, at(bob, 1, 4))
    _entry(db, newer, at(newer, 1, 0))
    _entry(db, newer, at(newer, 1, 1))
    for day in range(6):
        _entry(db, staff, at(staff, 1, day))

    cohorts, total = _report(db)

    assert [cohort.week_start for cohort in cohorts] == [utc_week_start(newer.created_at), old_week]
    old = cohorts[1]
    assert old.retention == Retention(
        size=2, eligible=(2, 2, 2, 2), active=(2, 1, 0, 1), regular=(1, 0, 0, 1)
    )
    assert [row.source for row in old.sources] == ["alice", "bob"]
    assert old.sources[0].retention.size == 1  # the staff account with the same label is left out
    assert cohorts[0].sources[0].source == "unknown"
    assert cohorts[0].retention == Retention(
        size=1, eligible=(1, 1, 0, 0), active=(1, 0, None, None), regular=(1, 0, None, None)
    )
    assert total == Retention(
        size=3, eligible=(3, 3, 2, 2), active=(3, 1, 0, 1), regular=(2, 0, 0, 1)
    )


def test_cohort_sources_sorted_by_size_then_name(db: Session) -> None:
    week = MONDAY - 2 * WEEK
    _user(db, created_at=week + timedelta(hours=1), source="zed")
    _user(db, created_at=week + timedelta(hours=2), source="zed")
    _user(db, created_at=week + timedelta(hours=3), source="bea")
    _user(db, created_at=week + timedelta(hours=4), source="amy")

    cohorts, _total = _report(db)

    assert [row.source for row in cohorts[0].sources] == ["zed", "amy", "bea"]
    assert cohorts[0].retention.size == 4


def test_week_boundary_and_same_local_day(db: Session) -> None:
    signup = MONDAY - 3 * WEEK + timedelta(hours=10)
    user = _user(db, created_at=signup, source="edge")
    _entry(db, user, signup + timedelta(hours=1))
    _entry(db, user, signup + timedelta(hours=2))  # same local day: still one day
    _entry(db, user, signup + WEEK)  # exactly seven days later: already W2

    retention = _by_source(_report(db)[0])["edge"]

    assert retention.active[:2] == (1, 1)
    assert retention.regular[:2] == (0, 0)


def test_local_day_follows_user_timezone(db: Session) -> None:
    signup = MONDAY - 3 * WEEK + timedelta(hours=10)
    minsk = _user(db, created_at=signup, source="minsk", tz="Europe/Minsk")
    utc = _user(db, created_at=signup, source="utc")
    for user in (minsk, utc):
        _entry(db, user, signup + timedelta(hours=10))  # 20:00 UTC, 23:00 in Minsk
        _entry(db, user, signup + timedelta(hours=12, minutes=30))  # 22:30 UTC, 01:30 next day

    by_source = _by_source(_report(db)[0])

    assert by_source["minsk"].regular[0] == 1
    assert by_source["utc"].regular[0] == 0
    assert by_source["utc"].active[0] == 1


def test_restored_entries_and_entries_before_signup_do_not_count(db: Session) -> None:
    signup = MONDAY - 3 * WEEK
    user = _user(db, created_at=signup, source="restored")
    restore = DiaryRestore(user_id=user.id, status="applied", format_version=1)
    db.add(restore)
    db.flush()
    _entry(db, user, signup - timedelta(days=1))
    _entry(db, user, signup + timedelta(days=1), restore_id=restore.id)
    _entry(db, user, signup + timedelta(days=2), restore_id=restore.id)

    retention = _by_source(_report(db)[0])["restored"]

    assert retention.active[0] == 0
    assert retention.regular[0] == 0


def test_week_counts_only_once_it_has_ended(db: Session) -> None:
    exactly_one_week = _user(db, created_at=NOW - WEEK, source="seven")
    almost = _user(db, created_at=NOW - WEEK + timedelta(seconds=1), source="almost")
    _entry(db, exactly_one_week, exactly_one_week.created_at + timedelta(hours=1))
    _entry(db, almost, almost.created_at + timedelta(hours=1))

    by_source = _by_source(_report(db)[0])

    assert by_source["seven"] == Retention(
        size=1, eligible=(1, 0, 0, 0), active=(1, None, None, None), regular=(0, None, None, None)
    )
    assert by_source["almost"] == Retention(
        size=1, eligible=(0, 0, 0, 0), active=(None,) * 4, regular=(None,) * 4
    )


def test_window_covers_whole_utc_weeks(db: Session) -> None:
    first_week = MONDAY - (COHORT_WEEKS - 1) * WEEK
    _user(db, created_at=first_week - timedelta(minutes=1), source="too-old")
    _user(db, created_at=first_week, source="first")
    _user(db, created_at=MONDAY - timedelta(minutes=30), source="sunday")
    _user(db, created_at=NOW + timedelta(minutes=1), source="future")

    cohorts, total = _report(db)

    weeks = {row.source: cohort.week_start for cohort in cohorts for row in cohort.sources}
    assert weeks == {"first": first_week, "sunday": MONDAY - WEEK}
    assert total.size == 2


def test_no_signups_gives_empty_cohorts(db: Session) -> None:
    cohorts, total = _report(db)

    assert cohorts == []
    assert total == Retention(
        size=0, eligible=(0, 0, 0, 0), active=(None,) * 4, regular=(None,) * 4
    )
