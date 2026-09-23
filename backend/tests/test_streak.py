from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.streak import check_in_date, current_streak, local_date


def test_current_streak_empty() -> None:
    today = date(2026, 8, 27)
    assert current_streak([], today=today) == 0


def test_current_streak_today_only() -> None:
    today = date(2026, 8, 27)
    assert current_streak([today], today=today) == 1


def test_current_streak_consecutive_including_today() -> None:
    today = date(2026, 8, 27)
    dates = [today - timedelta(days=offset) for offset in range(5)]
    assert current_streak(dates, today=today) == 5


def test_current_streak_keeps_yesterday_when_today_missing() -> None:
    today = date(2026, 8, 27)
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)
    assert current_streak([yesterday, day_before], today=today) == 2


def test_current_streak_breaks_after_missing_yesterday() -> None:
    today = date(2026, 8, 27)
    assert current_streak([today - timedelta(days=2)], today=today) == 0


def test_current_streak_stops_at_gap() -> None:
    today = date(2026, 8, 27)
    dates = [today, today - timedelta(days=1), today - timedelta(days=3)]
    assert current_streak(dates, today=today) == 2


def test_current_streak_westward_shift_keeps_run_from_tomorrow() -> None:
    today = date(2026, 8, 27)
    dates = [today + timedelta(days=1), today, today - timedelta(days=1)]
    assert current_streak(dates, today=today) == 3


def test_current_streak_tomorrow_only_survives_westward_shift() -> None:
    today = date(2026, 8, 27)
    assert current_streak([today + timedelta(days=1)], today=today) == 1


def test_current_streak_ignores_dates_beyond_tomorrow() -> None:
    today = date(2026, 8, 27)
    assert current_streak([today + timedelta(days=2)], today=today) == 0


def test_check_in_date_same_local_day() -> None:
    tz = ZoneInfo("Europe/Minsk")
    recorded = datetime(2026, 8, 27, 8, 0, tzinfo=tz)
    written = datetime(2026, 8, 27, 21, 30, tzinfo=tz)
    assert check_in_date(recorded, written, tz=tz) == date(2026, 8, 27)


def test_check_in_date_rejects_backdated_entry() -> None:
    tz = ZoneInfo("Europe/Minsk")
    recorded = datetime(2026, 8, 25, 12, 0, tzinfo=tz)
    written = datetime(2026, 8, 27, 12, 0, tzinfo=tz)
    assert check_in_date(recorded, written, tz=tz) is None


def test_check_in_date_rejects_future_dated_entry() -> None:
    tz = ZoneInfo("Europe/Minsk")
    recorded = datetime(2026, 8, 28, 9, 0, tzinfo=tz)
    written = datetime(2026, 8, 27, 21, 0, tzinfo=tz)
    assert check_in_date(recorded, written, tz=tz) is None


def test_check_in_date_uses_write_timezone_not_utc() -> None:
    tz = ZoneInfo("Pacific/Auckland")
    # 2026-08-27 00:30 NZST is still 2026-08-26 in UTC.
    instant = datetime(2026, 8, 26, 12, 30, tzinfo=UTC)
    assert local_date(instant, tz) == date(2026, 8, 27)
    assert check_in_date(instant, instant, tz=tz) == date(2026, 8, 27)
