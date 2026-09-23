"""Month mood index and month-over-month comparison.

This module is the single source of truth for analytics coefficients.
Tune the named constants below; do not scatter magic numbers in services.

===============================================================================
Design goals
===============================================================================

1. **Day is the primary unit.** A day with five sad entries must not weigh five
   times more in the monthly index than a day with one sad entry.
2. **Same-score repeats on one day dampen.** Logging the same emotion many
   times in one day should matter less than a single, distinct reading.
3. **One bad (or great) day should not dominate the month.** The monthly index
   is the mean of *active day* indices, so each logged day contributes equally.
4. **Sparse logging is OK.** Days without entries are ignored (they do not
   pull the month toward neutral).

===============================================================================
Pipeline
===============================================================================

Entries are first grouped by the user's local calendar day.

### Step A — same-score within-day weights

For scores on one day in chronological order, keep a per-score counter
``k`` (0-based). Weight of the next occurrence of that score:

    w = SAME_SCORE_DECAY ** k

Different scores on the same day do **not** share a counter: the first
``great`` and the first ``awful`` on that day each get weight ``1.0``.

Example (SAME_SCORE_DECAY = 0.55), day scores ``[1, 1, 1, 5]``:

| order | score | k | weight |
|-------|-------|---|--------|
| 1st   | 1     | 0 | 1.000  |
| 2nd   | 1     | 1 | 0.550  |
| 3rd   | 1     | 2 | 0.303  |
| 4th   | 5     | 0 | 1.000  |

The single ``5`` keeps full weight while repeated ``1``s fade.

### Step B — day mood index

    day_index = Σ(score_i × w_i) / Σ(w_i)

Result is in ``[MIN_MOOD_SCORE, MAX_MOOD_SCORE]`` (1–5).

A day of only identical scores still collapses to that score (e.g. five
``awful`` → day_index = 1). Dampening matters when scores *mix* on a day,
and when deciding how much within-day spam can bias the day mean.

### Step C — month mood index

Only **active days** (days with ≥1 entry) participate:

    month_index = mean(day_index for each active day)

Empty days are skipped. Therefore:

* 1 sad day + 19 good days → month stays near the good mean;
* 5 sad entries on one day still count as **one** day toward the month.

### Step D — compare with previous calendar month

    delta = current_month_index − previous_month_index

Both months need at least ``MIN_ACTIVE_DAYS_FOR_COMPARISON`` active days;
otherwise the verdict is ``insufficient_data``.

| condition                         | verdict        |
|-----------------------------------|----------------|
| \|delta\| < SIMILAR_ABS_DELTA     | similar        |
| SIMILAR ≤ \|delta\| < STRONG      | better / worse |
| \|delta\| ≥ STRONG_ABS_DELTA      | much_better / much_worse |

Signs: positive delta → better; negative → worse.

===============================================================================
Tuning guide
===============================================================================

* **SAME_SCORE_DECAY** closer to ``1.0`` → repeats count almost fully.
  Closer to ``0.0`` → only the first of each score that day matters.
* **MIN_ACTIVE_DAYS_FOR_COMPARISON** higher → fewer, more reliable verdicts.
* **SIMILAR_ABS_DELTA** / **STRONG_ABS_DELTA** — on the 1–5 scale.
  ``0.20`` ≈ a modest shift; ``0.45`` ≈ nearly half a mood step.

Keep ``SIMILAR_ABS_DELTA < STRONG_ABS_DELTA``.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.core.i18n import LocaleLabels, resolve_label
from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE

# --- Tunable coefficients (see module docstring) -----------------------------

# Each extra identical score on the same day multiplies weight by this factor.
SAME_SCORE_DECAY: float = 0.55

# Both months need at least this many days with entries to compare.
MIN_ACTIVE_DAYS_FOR_COMPARISON: int = 3

# |delta| below this → "similar" (mood scale units, 1–5).
SIMILAR_ABS_DELTA: float = 0.20

# |delta| at or above this → "much_better" / "much_worse".
STRONG_ABS_DELTA: float = 0.45

# -----------------------------------------------------------------------------


class MoodComparisonVerdict(StrEnum):
    MUCH_BETTER = "much_better"
    BETTER = "better"
    SIMILAR = "similar"
    WORSE = "worse"
    MUCH_WORSE = "much_worse"
    INSUFFICIENT_DATA = "insufficient_data"


VERDICT_MESSAGES: dict[MoodComparisonVerdict, LocaleLabels] = {
    MoodComparisonVerdict.MUCH_BETTER: {
        "en": "This month you feel much better than last month.",
        "ru": "В этом месяце вы чувствуете себя заметно лучше, чем в прошлом.",
    },
    MoodComparisonVerdict.BETTER: {
        "en": "This month you feel better than last month.",
        "ru": "В этом месяце вы чувствуете себя лучше, чем в прошлом.",
    },
    MoodComparisonVerdict.SIMILAR: {
        "en": "Your mood this month is similar to last month.",
        "ru": "Ваше настроение в этом месяце похоже на прошлый.",
    },
    MoodComparisonVerdict.WORSE: {
        "en": "This month you feel worse than last month.",
        "ru": "В этом месяце вы чувствуете себя хуже, чем в прошлом.",
    },
    MoodComparisonVerdict.MUCH_WORSE: {
        "en": "This month you feel much worse than last month.",
        "ru": "В этом месяце вы чувствуете себя заметно хуже, чем в прошлом.",
    },
    MoodComparisonVerdict.INSUFFICIENT_DATA: {
        "en": "Not enough entries yet to compare with last month.",
        "ru": "Пока недостаточно записей, чтобы сравнить с прошлым месяцем.",
    },
}


@dataclass(frozen=True, slots=True)
class MoodPeriodIndex:
    """Aggregated mood for one period (typically a calendar month)."""

    month_index: float | None
    active_days: int
    entry_count: int


@dataclass(frozen=True, slots=True)
class MoodMonthComparison:
    verdict: MoodComparisonVerdict
    message: str
    current_index: float | None
    previous_index: float | None
    delta: float | None
    current_active_days: int
    previous_active_days: int


def same_score_weight(occurrence_index: int) -> float:
    """Weight for the n-th occurrence (0-based) of a score on one day."""
    if occurrence_index < 0:
        raise ValueError("occurrence_index must be >= 0")
    return SAME_SCORE_DECAY**occurrence_index


def day_mood_index(scores_chronological: Sequence[int]) -> float:
    """Weighted mean of scores for a single day (same-score decay)."""
    if not scores_chronological:
        raise ValueError("scores_chronological must not be empty")

    seen: dict[int, int] = defaultdict(int)
    weighted_sum = 0.0
    weight_sum = 0.0
    for score in scores_chronological:
        if score < MIN_MOOD_SCORE or score > MAX_MOOD_SCORE:
            raise ValueError(f"score out of range: {score}")
        weight = same_score_weight(seen[score])
        seen[score] += 1
        weighted_sum += score * weight
        weight_sum += weight
    return weighted_sum / weight_sum


def period_index_from_day_scores(
    days: Mapping[date, Sequence[int]],
) -> MoodPeriodIndex:
    """Build a period index from ``{local_date: scores in chronological order}``."""
    if not days:
        return MoodPeriodIndex(month_index=None, active_days=0, entry_count=0)

    day_indices: list[float] = []
    entry_count = 0
    for scores in days.values():
        if not scores:
            continue
        entry_count += len(scores)
        day_indices.append(day_mood_index(scores))

    if not day_indices:
        return MoodPeriodIndex(month_index=None, active_days=0, entry_count=0)

    return MoodPeriodIndex(
        month_index=sum(day_indices) / len(day_indices),
        active_days=len(day_indices),
        entry_count=entry_count,
    )


def group_scores_by_day(
    rows: Iterable[tuple[date, int, datetime]],
) -> dict[date, list[int]]:
    """Group ``(local_date, score, recorded_at)`` into chronological score lists."""
    buckets: dict[date, list[tuple[datetime, int]]] = defaultdict(list)
    for local_date, score, recorded_at in rows:
        buckets[local_date].append((recorded_at, score))

    result: dict[date, list[int]] = {}
    for local_date, items in buckets.items():
        items.sort(key=lambda item: item[0])
        result[local_date] = [score for _, score in items]
    return result


def compare_month_indices(
    current: MoodPeriodIndex,
    previous: MoodPeriodIndex,
    *,
    locale: str,
) -> MoodMonthComparison:
    """Map two period indices to a comparison verdict and localized message."""
    current_ok = (
        current.month_index is not None and current.active_days >= MIN_ACTIVE_DAYS_FOR_COMPARISON
    )
    previous_ok = (
        previous.month_index is not None and previous.active_days >= MIN_ACTIVE_DAYS_FOR_COMPARISON
    )

    if not current_ok or not previous_ok:
        return MoodMonthComparison(
            verdict=MoodComparisonVerdict.INSUFFICIENT_DATA,
            message=resolve_label(
                VERDICT_MESSAGES[MoodComparisonVerdict.INSUFFICIENT_DATA],
                locale,
            ),
            current_index=current.month_index,
            previous_index=previous.month_index,
            delta=None,
            current_active_days=current.active_days,
            previous_active_days=previous.active_days,
        )

    assert current.month_index is not None
    assert previous.month_index is not None
    delta = current.month_index - previous.month_index
    abs_delta = abs(delta)

    if abs_delta < SIMILAR_ABS_DELTA:
        verdict = MoodComparisonVerdict.SIMILAR
    elif delta > 0:
        verdict = (
            MoodComparisonVerdict.MUCH_BETTER
            if abs_delta >= STRONG_ABS_DELTA
            else MoodComparisonVerdict.BETTER
        )
    else:
        verdict = (
            MoodComparisonVerdict.MUCH_WORSE
            if abs_delta >= STRONG_ABS_DELTA
            else MoodComparisonVerdict.WORSE
        )

    return MoodMonthComparison(
        verdict=verdict,
        message=resolve_label(VERDICT_MESSAGES[verdict], locale),
        current_index=current.month_index,
        previous_index=previous.month_index,
        delta=delta,
        current_active_days=current.active_days,
        previous_active_days=previous.active_days,
    )


def previous_calendar_month_start(month_start_local: date) -> date:
    """Return the first day of the calendar month before ``month_start_local``."""
    if month_start_local.month == 1:
        return date(month_start_local.year - 1, 12, 1)
    return date(month_start_local.year, month_start_local.month - 1, 1)
