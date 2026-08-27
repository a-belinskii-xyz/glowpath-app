from datetime import date, timedelta

from app.core.streak import current_streak


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


def test_current_streak_ignores_future_dates() -> None:
    today = date(2026, 8, 27)
    dates = [today + timedelta(days=1), today, today - timedelta(days=1)]
    assert current_streak(dates, today=today) == 2


def test_current_streak_future_only_is_zero() -> None:
    today = date(2026, 8, 27)
    assert current_streak([today + timedelta(days=1)], today=today) == 0
