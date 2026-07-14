"""Unit tests for mood month-index formulas and comparison thresholds."""

from datetime import UTC, date, datetime

from app.core.mood_analytics import (
    MIN_ACTIVE_DAYS_FOR_COMPARISON,
    SAME_SCORE_DECAY,
    SIMILAR_ABS_DELTA,
    STRONG_ABS_DELTA,
    MoodComparisonVerdict,
    MoodPeriodIndex,
    compare_month_indices,
    day_mood_index,
    group_scores_by_day,
    period_index_from_day_scores,
    previous_calendar_month_start,
    same_score_weight,
)


def test_same_score_weights_decay() -> None:
    assert same_score_weight(0) == 1.0
    assert same_score_weight(1) == SAME_SCORE_DECAY
    assert same_score_weight(2) == SAME_SCORE_DECAY**2


def test_day_index_identical_scores_stays_flat() -> None:
    # Five awful entries still mean an awful day — dampening doesn't invent mood.
    assert day_mood_index([1, 1, 1, 1, 1]) == 1.0
    assert day_mood_index([5]) == 5.0


def test_day_index_repeated_sad_weighs_less_than_single_great() -> None:
    # Without decay, [1,1,1,5] mean = 2.0. With decay the single 5 pulls higher.
    plain_mean = sum([1, 1, 1, 5]) / 4
    weighted = day_mood_index([1, 1, 1, 5])
    assert weighted > plain_mean
    assert weighted > 2.3


def test_one_bad_day_does_not_ruin_month() -> None:
    days = {date(2026, 7, day): [5] for day in range(1, 20)}
    days[date(2026, 7, 20)] = [1, 1, 1, 1, 1]  # awful spam, still one day
    period = period_index_from_day_scores(days)
    assert period.active_days == 20
    assert period.month_index is not None
    # 19×5 + 1×1 = 96 / 20 = 4.8
    assert period.month_index == 4.8


def test_group_scores_orders_chronologically() -> None:
    rows = [
        (date(2026, 7, 14), 3, datetime(2026, 7, 14, 15, tzinfo=UTC)),
        (date(2026, 7, 14), 1, datetime(2026, 7, 14, 9, tzinfo=UTC)),
        (date(2026, 7, 14), 5, datetime(2026, 7, 14, 18, tzinfo=UTC)),
        (date(2026, 7, 15), 4, datetime(2026, 7, 15, 10, tzinfo=UTC)),
    ]
    grouped = group_scores_by_day(rows)
    assert grouped[date(2026, 7, 14)] == [1, 3, 5]
    assert grouped[date(2026, 7, 15)] == [4]


def test_compare_insufficient_when_too_few_days() -> None:
    current = MoodPeriodIndex(
        month_index=4.0, active_days=MIN_ACTIVE_DAYS_FOR_COMPARISON - 1, entry_count=2
    )
    previous = MoodPeriodIndex(month_index=3.0, active_days=10, entry_count=10)
    result = compare_month_indices(current, previous, locale="en")
    assert result.verdict == MoodComparisonVerdict.INSUFFICIENT_DATA
    assert result.delta is None


def test_compare_verdicts_by_delta() -> None:
    previous = MoodPeriodIndex(month_index=3.0, active_days=10, entry_count=10)

    similar = compare_month_indices(
        MoodPeriodIndex(month_index=3.0 + SIMILAR_ABS_DELTA / 2, active_days=10, entry_count=10),
        previous,
        locale="en",
    )
    assert similar.verdict == MoodComparisonVerdict.SIMILAR

    better = compare_month_indices(
        MoodPeriodIndex(
            month_index=3.0 + (SIMILAR_ABS_DELTA + STRONG_ABS_DELTA) / 2,
            active_days=10,
            entry_count=10,
        ),
        previous,
        locale="en",
    )
    assert better.verdict == MoodComparisonVerdict.BETTER

    much_better = compare_month_indices(
        MoodPeriodIndex(month_index=3.0 + STRONG_ABS_DELTA, active_days=10, entry_count=10),
        previous,
        locale="en",
    )
    assert much_better.verdict == MoodComparisonVerdict.MUCH_BETTER
    assert "much better" in much_better.message

    worse = compare_month_indices(
        MoodPeriodIndex(
            month_index=3.0 - (SIMILAR_ABS_DELTA + STRONG_ABS_DELTA) / 2,
            active_days=10,
            entry_count=10,
        ),
        previous,
        locale="ru",
    )
    assert worse.verdict == MoodComparisonVerdict.WORSE
    assert "хуже" in worse.message


def test_previous_calendar_month_start() -> None:
    assert previous_calendar_month_start(date(2026, 7, 1)) == date(2026, 6, 1)
    assert previous_calendar_month_start(date(2026, 1, 1)) == date(2025, 12, 1)
