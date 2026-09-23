"""Personal mood-pattern insights (weekday, time of day, tags).

This module is the single source of truth for insight formulas and thresholds.
Tune the named constants below; do not scatter magic numbers in services.

A pattern is shown only when it is *large enough* and *seen often enough* to
be worth the user's attention. We never report "Monday is 0.05 higher".

===============================================================================
Design goals
===============================================================================

1. **Day is the primary unit** (same as ``mood_analytics``). Five sad entries
   on one Saturday must not count as five independent Saturdays.
2. **Contrast beats raw averages.** "Saturdays average 4.2" is trivia;
   "Saturdays are 0.8 above other days" is a pattern.
3. **The smaller arm limits confidence.** 2 great Saturdays vs 40 other days
   is a spike, not a habit. Reliability uses the harmonic mean of sample sizes.
4. **Silence is better than a weak card.** Empty ``items`` is a valid product
   state — we do not invent stories from three check-ins.
5. **One story per kind.** Return a short mix (weekend, time of day, tag),
   not ten overlapping cards about Saturday.

===============================================================================
Pipeline
===============================================================================

Entries (in the user's timezone) are folded into ``DayBundle`` rows:

* ``day_index`` — ``day_mood_index`` of that day's scores (same-score decay).
* ``dayparts`` — the same index, but only scores that fall in a time-of-day bin.
* ``tag_ids`` — union of tags used that day.

Candidates are contrasts. Each contrast must pass:

    n_group      >= MIN_GROUP_DAYS
    n_complement >= MIN_COMPLEMENT_DAYS
    |effect|     >= threshold for that kind

Then we rank by reliability and pick at most one insight per ``InsightKind``.

===============================================================================
Formulas
===============================================================================

### Day index (reused)

    day_index = day_mood_index(scores that day)

See ``mood_analytics``: same-score repeats on one day decay so spam cannot
dominate a Saturday or a "walk" day.

### Contrast delta (mood-scale kinds)

For a group of days G and its complement C (the other active days):

    mean_G = mean(day_index for days in G)
    mean_C = mean(day_index for days in C)
    delta  = mean_G − mean_C

``delta > 0`` → the group runs higher than the rest; ``delta < 0`` → lower.

Time-of-day uses the same delta, but the unit is the *bin* index
``dayparts[part]`` rather than the full-day index. A day can contribute to
both afternoon and evening; this is an unpaired between-bin comparison.
The paired version is ``within_day`` (below).

### Reliability

    H = 2 / (1/n_G + 1/n_C)     # harmonic mean of the two arms
    reliability = |effect| × √H

Why harmonic mean: a 2-vs-40 split of the same |delta| is less trustworthy
than 8-vs-8. Why square root: the 16th day should not be worth four times
the 4th — diminishing returns, not a p-value.

### Strength

On the 1–5 mood scale (delta kinds):

| |delta|                         | strength |
|---------------------------------|----------|
| MIN_INTERESTING_DELTA … STRONG  | modest   |
| >= STRONG_ABS_DELTA             | strong   |

``STRONG_ABS_DELTA`` is shared with month-over-month comparison so "strong"
means the same size of shift the user already sees on the month card.

### Weekend vs weekday

    G = Saturday ∪ Sunday
    C = Monday … Friday

This is usually more stable than a single weekday (more days in G).

### Single weekday

    G = that weekday
    C = all other active days

Emitted only if it still clears the thresholds. Ranking + diversity decide
whether the weekend card or e.g. "Saturdays" wins.

### Time of day (unpaired)

Bins (local hour, inclusive start, inclusive end):

| bin        | hours        |
|------------|--------------|
| morning    | 05–11        |
| afternoon  | 12–16        |
| evening    | 17–21        |
| night      | 22–04        |

For each (day, bin) with at least one score, ``dayparts[bin]`` is
``day_mood_index`` of *that bin's* scores (decay is per bin, not per day).

We compare every pair of bins that both have ``>= MIN_DAYPART_DAYS`` days
and keep the pair with the largest |delta|. That is the "afternoons run
higher than evenings" card.

### Within-day slope (paired)

For days that have both an *earlier* bin (morning and/or afternoon) and an
evening bin:

    earlier = day_mood_index(morning ∪ afternoon scores)
    delta_day = evening − earlier

    mean_delta = mean(delta_day)

This asks a different question than unpaired bins: *on the same day*, does
evening drop? Pairing removes "I only log evenings when I feel bad".

### Tag → mood

    G = days that used the tag at least once
    C = active days that did not

Same delta as weekday. A tag that sits on almost every day fails
``MIN_COMPLEMENT_DAYS`` (there is no contrast). A tag used on two days
fails ``MIN_GROUP_DAYS``.

### Mood → tag (lift)

A day is *bright* when ``day_index >= HIGH_DAY_INDEX`` (good/great territory).

    P(tag | bright) = |bright days with tag| / |bright days|
    P(tag)          = |days with tag| / |active days|
    lift            = P(tag | bright) / P(tag)

``lift > 1`` → the tag shows up *more* on brighter days ("when you feel
good you socialize"). ``lift < 1`` → less often (anxiety on good days).

Reliability uses ``log(lift)`` as the effect so a 2× lift is in the same
ballpark as a ~0.7 mood-scale delta, not a raw "2.0 vs 0.7" mismatch.

Lift kinds use:

| lift or 1/lift | strength |
|----------------|----------|
| MIN_LIFT … STRONG_LIFT | modest |
| >= STRONG_LIFT         | strong |

===============================================================================
Tuning guide
===============================================================================

* **MIN_ACTIVE_DAYS_FOR_INSIGHTS** — whole-window floor before any card.
* **MIN_GROUP_DAYS / MIN_COMPLEMENT_DAYS** — raise to be stricter; lower
  only if you accept noisier early cards.
* **MIN_INTERESTING_DELTA** should stay **>= SIMILAR_ABS_DELTA** so we do
  not call a "similar" month-shift an interesting weekday pattern.
* **HIGH_DAY_INDEX** closer to 5 → fewer bright days, rarer mood→tag cards.
* **FOCUS_BOOST** only reorders already-qualified cards (post-save); it
  never lowers a threshold.
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum

from app.core.i18n import LocaleLabels, normalize_locale, resolve_label
from app.core.mood_analytics import STRONG_ABS_DELTA, day_mood_index
from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE, MoodScore, mood_score_label

# --- Tunable coefficients (see module docstring) -----------------------------

# Rolling window when the client omits recorded_from / recorded_to.
INSIGHT_DEFAULT_LOOKBACK_DAYS: int = 56

# Hard cap so a 2-year dump cannot turn insights into a full-table scan.
INSIGHT_MAX_WINDOW_DAYS: int = 180

# Do not emit any card until the window has this many distinct logged days.
MIN_ACTIVE_DAYS_FOR_INSIGHTS: int = 8

# Smaller arm of a contrast (the group the sentence is about).
MIN_GROUP_DAYS: int = 3

# Larger / other arm. A 3-vs-2 split is not a pattern yet.
MIN_COMPLEMENT_DAYS: int = 4

# Time-of-day bins need a bit more — hours are noisier than weekdays.
MIN_DAYPART_DAYS: int = 4

# Paired evening-vs-earlier days.
MIN_PAIRED_DAYS: int = 4

# Mood → tag: enough bright days to estimate a share.
MIN_HIGH_DAYS: int = 4

# At least this many bright days must carry the tag (one lucky day ≠ habit).
MIN_TAGGED_HIGH_DAYS: int = 2

# |delta| on the 1–5 scale below this is "similar", not a card.
# Kept at/above mood_analytics.SIMILAR_ABS_DELTA (0.20).
MIN_INTERESTING_DELTA: float = 0.25

# Paired within-day uses the same floor; pairing already adds confidence.
MIN_WITHIN_DAY_DELTA: float = 0.25

# Bright day: day index in good/great territory (4 = "good").
HIGH_DAY_INDEX: float = 4.0

# Lift below this (or 1/lift for "less often") is not interesting.
MIN_LIFT: float = 1.45

# Lift at or above this → strength "strong".
STRONG_LIFT: float = 2.0

# Multiply reliability when the card matches the just-saved entry.
FOCUS_BOOST: float = 1.4

# How many cards the API returns by default / max (service also clamps).
DEFAULT_INSIGHT_LIMIT: int = 4
MAX_INSIGHT_LIMIT: int = 8

# -----------------------------------------------------------------------------

_WEEKEND_DAYS: frozenset[int] = frozenset({5, 6})


class InsightKind(StrEnum):
    WEEKEND = "weekend"
    WEEKDAY = "weekday"
    DAYPART = "daypart"
    WITHIN_DAY = "within_day"
    TAG_MOOD = "tag_mood"
    MOOD_TAG = "mood_tag"


class InsightDirection(StrEnum):
    HIGHER = "higher"
    LOWER = "lower"
    MORE_OFTEN = "more_often"
    LESS_OFTEN = "less_often"


class InsightStrength(StrEnum):
    MODEST = "modest"
    STRONG = "strong"


class InsightSubjectType(StrEnum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    WEEKDAY_BAND = "weekday_band"
    DAYPART = "daypart"
    TAG = "tag"


class Daypart(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


_EARLIER_DAYPARTS = frozenset({Daypart.MORNING, Daypart.AFTERNOON})


# Monday = 0 … Sunday = 6, matching ``datetime.date.weekday``.
WEEKDAY_NAME_LABELS: dict[int, LocaleLabels] = {
    0: {"en": "Mondays", "ru": "Понедельники"},
    1: {"en": "Tuesdays", "ru": "Вторники"},
    2: {"en": "Wednesdays", "ru": "Среды"},
    3: {"en": "Thursdays", "ru": "Четверги"},
    4: {"en": "Fridays", "ru": "Пятницы"},
    5: {"en": "Saturdays", "ru": "Субботы"},
    6: {"en": "Sundays", "ru": "Воскресенья"},
}

# Dative / "on Fridays" form for body sentences.
WEEKDAY_ON_LABELS: dict[int, LocaleLabels] = {
    0: {"en": "Mondays", "ru": "понедельникам"},
    1: {"en": "Tuesdays", "ru": "вторникам"},
    2: {"en": "Wednesdays", "ru": "средам"},
    3: {"en": "Thursdays", "ru": "четвергам"},
    4: {"en": "Fridays", "ru": "пятницам"},
    5: {"en": "Saturdays", "ru": "субботам"},
    6: {"en": "Sundays", "ru": "воскресеньям"},
}

# Counted weekday nouns for sample lines (1 Monday / 4 Fridays / 4 пятницы).
WEEKDAY_COUNT_FORMS: dict[int, dict[str, LocaleLabels]] = {
    0: {
        "one": {"en": "Monday", "ru": "понедельник"},
        "few": {"en": "Mondays", "ru": "понедельника"},
        "many": {"en": "Mondays", "ru": "понедельников"},
    },
    1: {
        "one": {"en": "Tuesday", "ru": "вторник"},
        "few": {"en": "Tuesdays", "ru": "вторника"},
        "many": {"en": "Tuesdays", "ru": "вторников"},
    },
    2: {
        "one": {"en": "Wednesday", "ru": "среда"},
        "few": {"en": "Wednesdays", "ru": "среды"},
        "many": {"en": "Wednesdays", "ru": "сред"},
    },
    3: {
        "one": {"en": "Thursday", "ru": "четверг"},
        "few": {"en": "Thursdays", "ru": "четверга"},
        "many": {"en": "Thursdays", "ru": "четвергов"},
    },
    4: {
        "one": {"en": "Friday", "ru": "пятница"},
        "few": {"en": "Fridays", "ru": "пятницы"},
        "many": {"en": "Fridays", "ru": "пятниц"},
    },
    5: {
        "one": {"en": "Saturday", "ru": "суббота"},
        "few": {"en": "Saturdays", "ru": "субботы"},
        "many": {"en": "Saturdays", "ru": "суббот"},
    },
    6: {
        "one": {"en": "Sunday", "ru": "воскресенье"},
        "few": {"en": "Sundays", "ru": "воскресенья"},
        "many": {"en": "Sundays", "ru": "воскресений"},
    },
}

WEEKDAY_KEY: dict[int, str] = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}

DAYPART_LABELS: dict[Daypart, LocaleLabels] = {
    Daypart.MORNING: {"en": "morning", "ru": "утром"},
    Daypart.AFTERNOON: {"en": "afternoon", "ru": "днём"},
    Daypart.EVENING: {"en": "evening", "ru": "вечером"},
    Daypart.NIGHT: {"en": "night", "ru": "ночью"},
}

# Prepositional phrase for running text: "in the morning" / "утром".
DAYPART_AT_LABELS: dict[Daypart, LocaleLabels] = {
    Daypart.MORNING: {"en": "in the morning", "ru": "утром"},
    Daypart.AFTERNOON: {"en": "in the afternoon", "ru": "днём"},
    Daypart.EVENING: {"en": "in the evening", "ru": "вечером"},
    Daypart.NIGHT: {"en": "at night", "ru": "ночью"},
}

DAYPART_NOUN_LABELS: dict[Daypart, LocaleLabels] = {
    Daypart.MORNING: {"en": "mornings", "ru": "утро"},
    Daypart.AFTERNOON: {"en": "afternoons", "ru": "день"},
    Daypart.EVENING: {"en": "evenings", "ru": "вечер"},
    Daypart.NIGHT: {"en": "nights", "ru": "ночь"},
}


@dataclass(frozen=True, slots=True)
class MoodObservation:
    """One mood entry, already converted to the user's local clock."""

    local_date: date
    weekday: int
    hour: int
    daypart: Daypart
    score: int
    tag_ids: frozenset[uuid.UUID]
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class TagRef:
    id: uuid.UUID
    slug: str
    label: str
    color: str
    icon_type: str
    icon: str


@dataclass(frozen=True, slots=True)
class DayBundle:
    local_date: date
    weekday: int
    day_index: float
    tag_ids: frozenset[uuid.UUID]
    dayparts: Mapping[Daypart, float]
    daypart_scores: Mapping[Daypart, tuple[int, ...]]


@dataclass(frozen=True, slots=True)
class FocusContext:
    weekday: int
    daypart: Daypart
    tag_ids: frozenset[uuid.UUID]


@dataclass(frozen=True, slots=True)
class InsightSubject:
    type: InsightSubjectType
    key: str
    label: str
    tag: TagRef | None = None


@dataclass(frozen=True, slots=True)
class InsightCandidate:
    id: str
    kind: InsightKind
    direction: InsightDirection
    strength: InsightStrength
    title: str
    body: str
    sample: str
    delta: float | None
    lift: float | None
    group_mean: float | None
    complement_mean: float | None
    group_share: float | None
    complement_share: float | None
    group_n: int
    complement_n: int
    subjects: tuple[InsightSubject, ...]
    reliability: float


def daypart_for_hour(hour: int) -> Daypart:
    """Map a local hour (0–23) to a time-of-day bin.

    Boundaries are inclusive on the start hour. 17:00 is evening, not
    afternoon: that is when "after work" check-ins typically land, which is
    the contrast users mean by "evenings feel worse".
    """
    if hour < 0 or hour > 23:
        raise ValueError(f"hour out of range: {hour}")
    if 5 <= hour <= 11:
        return Daypart.MORNING
    if 12 <= hour <= 16:
        return Daypart.AFTERNOON
    if 17 <= hour <= 21:
        return Daypart.EVENING
    return Daypart.NIGHT


def contrast_reliability(*, effect: float, group_n: int, complement_n: int) -> float:
    """``|effect| × √(harmonic mean of n)``. See module docstring."""
    if group_n <= 0 or complement_n <= 0:
        return 0.0
    harmonic = 2.0 * group_n * complement_n / (group_n + complement_n)
    return abs(effect) * math.sqrt(harmonic)


def strength_for_delta(abs_delta: float) -> InsightStrength:
    if abs_delta >= STRONG_ABS_DELTA:
        return InsightStrength.STRONG
    return InsightStrength.MODEST


def strength_for_lift(lift: float) -> InsightStrength:
    ratio = lift if lift >= 1.0 else (1.0 / lift if lift > 0 else 0.0)
    if ratio >= STRONG_LIFT:
        return InsightStrength.STRONG
    return InsightStrength.MODEST


def direction_for_delta(delta: float) -> InsightDirection:
    return InsightDirection.HIGHER if delta >= 0 else InsightDirection.LOWER


def bundle_days(observations: Sequence[MoodObservation]) -> dict[date, DayBundle]:
    """Fold entries into one bundle per local calendar day."""
    by_day: dict[date, list[MoodObservation]] = defaultdict(list)
    for obs in observations:
        by_day[obs.local_date].append(obs)

    bundles: dict[date, DayBundle] = {}
    for local_date, rows in by_day.items():
        rows_sorted = sorted(rows, key=lambda item: item.recorded_at)
        scores = tuple(item.score for item in rows_sorted)
        tag_ids: set[uuid.UUID] = set()
        part_rows: dict[Daypart, list[MoodObservation]] = defaultdict(list)
        for item in rows_sorted:
            tag_ids.update(item.tag_ids)
            part_rows[item.daypart].append(item)

        dayparts: dict[Daypart, float] = {}
        daypart_scores: dict[Daypart, tuple[int, ...]] = {}
        for part, part_items in part_rows.items():
            part_scores = tuple(item.score for item in part_items)
            daypart_scores[part] = part_scores
            dayparts[part] = day_mood_index(part_scores)

        bundles[local_date] = DayBundle(
            local_date=local_date,
            weekday=rows_sorted[0].weekday,
            day_index=day_mood_index(scores),
            tag_ids=frozenset(tag_ids),
            dayparts=dayparts,
            daypart_scores=daypart_scores,
        )
    return bundles


def build_insights(
    observations: Sequence[MoodObservation],
    *,
    tags: Mapping[uuid.UUID, TagRef],
    locale: str,
    limit: int = DEFAULT_INSIGHT_LIMIT,
    focus: FocusContext | None = None,
) -> list[InsightCandidate]:
    """Return up to ``limit`` diverse, threshold-passing insight cards."""
    clamped = max(1, min(limit, MAX_INSIGHT_LIMIT))
    days = bundle_days(observations)
    if len(days) < MIN_ACTIVE_DAYS_FOR_INSIGHTS:
        return []

    candidates: list[InsightCandidate] = []
    candidates.extend(_weekend_candidates(days, locale=locale))
    candidates.extend(_weekday_candidates(days, locale=locale))
    candidates.extend(_daypart_candidates(days, locale=locale))
    candidates.extend(_within_day_candidates(days, locale=locale))
    candidates.extend(_tag_mood_candidates(days, tags=tags, locale=locale))
    candidates.extend(_mood_tag_candidates(days, tags=tags, locale=locale))

    if focus is not None:
        candidates = [_with_focus_boost(item, focus) for item in candidates]

    candidates.sort(key=lambda item: item.reliability, reverse=True)
    return _pick_diverse(candidates, limit=clamped)


def mean_or_none(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _delta_if_interesting(
    group: Sequence[float],
    complement: Sequence[float],
    *,
    min_delta: float = MIN_INTERESTING_DELTA,
) -> float | None:
    if len(group) < MIN_GROUP_DAYS or len(complement) < MIN_COMPLEMENT_DAYS:
        return None
    group_mean = sum(group) / len(group)
    complement_mean = sum(complement) / len(complement)
    delta = group_mean - complement_mean
    if abs(delta) < min_delta:
        return None
    return delta


def _weekend_candidates(
    days: Mapping[date, DayBundle],
    *,
    locale: str,
) -> list[InsightCandidate]:
    weekend = [day.day_index for day in days.values() if day.weekday in _WEEKEND_DAYS]
    weekdays = [day.day_index for day in days.values() if day.weekday not in _WEEKEND_DAYS]
    delta = _delta_if_interesting(weekend, weekdays)
    if delta is None:
        return []
    direction = direction_for_delta(delta)
    weekend_mean = sum(weekend) / len(weekend)
    weekday_mean = sum(weekdays) / len(weekdays)
    title_key = (
        "weekend_higher_title" if direction is InsightDirection.HIGHER else "weekend_lower_title"
    )
    body_key = (
        "weekend_higher_body" if direction is InsightDirection.HIGHER else "weekend_lower_body"
    )
    params = _contrast_params(weekend_mean, weekday_mean, locale)
    return [
        InsightCandidate(
            id=f"weekend:weekend:{direction.value}",
            kind=InsightKind.WEEKEND,
            direction=direction,
            strength=strength_for_delta(abs(delta)),
            title=_message(title_key, locale, params),
            body=_message(body_key, locale, params),
            sample=_sample_weekend(
                weekend_n=len(weekend),
                weekday_n=len(weekdays),
                locale=locale,
            ),
            delta=delta,
            lift=None,
            group_mean=weekend_mean,
            complement_mean=weekday_mean,
            group_share=None,
            complement_share=None,
            group_n=len(weekend),
            complement_n=len(weekdays),
            subjects=(
                InsightSubject(
                    type=InsightSubjectType.WEEKEND,
                    key="weekend",
                    label=_message("weekend_label", locale, {}),
                ),
                InsightSubject(
                    type=InsightSubjectType.WEEKDAY_BAND,
                    key="weekdays",
                    label=_message("weekdays_label", locale, {}),
                ),
            ),
            reliability=contrast_reliability(
                effect=delta,
                group_n=len(weekend),
                complement_n=len(weekdays),
            ),
        )
    ]


def _weekday_candidates(
    days: Mapping[date, DayBundle],
    *,
    locale: str,
) -> list[InsightCandidate]:
    by_weekday: dict[int, list[float]] = defaultdict(list)
    for day in days.values():
        by_weekday[day.weekday].append(day.day_index)

    results: list[InsightCandidate] = []
    for weekday, group in by_weekday.items():
        complement = [day.day_index for day in days.values() if day.weekday != weekday]
        delta = _delta_if_interesting(group, complement)
        if delta is None:
            continue
        direction = direction_for_delta(delta)
        group_mean = sum(group) / len(group)
        complement_mean = sum(complement) / len(complement)
        weekday_name = resolve_label(WEEKDAY_NAME_LABELS[weekday], locale)
        weekday_on = resolve_label(WEEKDAY_ON_LABELS[weekday], locale)
        key = WEEKDAY_KEY[weekday]
        title_key = (
            "weekday_higher_title"
            if direction is InsightDirection.HIGHER
            else "weekday_lower_title"
        )
        body_key = (
            "weekday_higher_body" if direction is InsightDirection.HIGHER else "weekday_lower_body"
        )
        params = {
            "weekday": weekday_name,
            "weekday_on": weekday_on,
            **_contrast_params(group_mean, complement_mean, locale),
        }
        results.append(
            InsightCandidate(
                id=f"weekday:{key}:{direction.value}",
                kind=InsightKind.WEEKDAY,
                direction=direction,
                strength=strength_for_delta(abs(delta)),
                title=_message(title_key, locale, params),
                body=_message(body_key, locale, params),
                sample=_sample_weekday(
                    weekday=weekday,
                    group_n=len(group),
                    complement_n=len(complement),
                    locale=locale,
                ),
                delta=delta,
                lift=None,
                group_mean=group_mean,
                complement_mean=complement_mean,
                group_share=None,
                complement_share=None,
                group_n=len(group),
                complement_n=len(complement),
                subjects=(
                    InsightSubject(
                        type=InsightSubjectType.WEEKDAY,
                        key=key,
                        label=weekday_name,
                    ),
                ),
                reliability=contrast_reliability(
                    effect=delta,
                    group_n=len(group),
                    complement_n=len(complement),
                ),
            )
        )
    return results


def _daypart_candidates(
    days: Mapping[date, DayBundle],
    *,
    locale: str,
) -> list[InsightCandidate]:
    by_part: dict[Daypart, list[float]] = defaultdict(list)
    for day in days.values():
        for part, index in day.dayparts.items():
            by_part[part].append(index)

    eligible = {part: values for part, values in by_part.items() if len(values) >= MIN_DAYPART_DAYS}
    if len(eligible) < 2:
        return []

    best: tuple[float, Daypart, Daypart, float, float] | None = None
    parts = list(eligible.keys())
    for i, left in enumerate(parts):
        for right in parts[i + 1 :]:
            left_vals = eligible[left]
            right_vals = eligible[right]
            left_mean = sum(left_vals) / len(left_vals)
            right_mean = sum(right_vals) / len(right_vals)
            delta = left_mean - right_mean
            if abs(delta) < MIN_INTERESTING_DELTA:
                continue
            if best is None or abs(delta) > abs(best[0]):
                best = (delta, left, right, left_mean, right_mean)

    if best is None:
        return []

    delta, left, right, left_mean, right_mean = best
    if delta >= 0:
        higher, lower = left, right
        higher_mean, lower_mean = left_mean, right_mean
        higher_n = len(eligible[left])
        lower_n = len(eligible[right])
    else:
        higher, lower = right, left
        higher_mean, lower_mean = right_mean, left_mean
        higher_n = len(eligible[right])
        lower_n = len(eligible[left])
        delta = -delta

    # Observation is about the later dip when evenings/nights are lower;
    # otherwise "usually better at X". Delta is stored as higher − lower.
    params = {
        "higher_at": resolve_label(DAYPART_AT_LABELS[higher], locale),
        "lower_at": resolve_label(DAYPART_AT_LABELS[lower], locale),
        "higher_at_cap": _cap_first(resolve_label(DAYPART_AT_LABELS[higher], locale)),
        **_contrast_params(higher_mean, lower_mean, locale),
    }
    return [
        InsightCandidate(
            id=f"daypart:{higher.value}_{lower.value}:higher",
            kind=InsightKind.DAYPART,
            direction=InsightDirection.HIGHER,
            strength=strength_for_delta(delta),
            title=_daypart_title(higher, lower, locale, params),
            body=_message("daypart_body", locale, params),
            sample=_sample_daypart(
                higher=higher,
                lower=lower,
                higher_n=higher_n,
                lower_n=lower_n,
                locale=locale,
            ),
            delta=delta,
            lift=None,
            group_mean=higher_mean,
            complement_mean=lower_mean,
            group_share=None,
            complement_share=None,
            group_n=higher_n,
            complement_n=lower_n,
            subjects=(
                InsightSubject(
                    type=InsightSubjectType.DAYPART,
                    key=higher.value,
                    label=resolve_label(DAYPART_LABELS[higher], locale),
                ),
                InsightSubject(
                    type=InsightSubjectType.DAYPART,
                    key=lower.value,
                    label=resolve_label(DAYPART_LABELS[lower], locale),
                ),
            ),
            reliability=contrast_reliability(
                effect=delta,
                group_n=higher_n,
                complement_n=lower_n,
            ),
        )
    ]


def _within_day_candidates(
    days: Mapping[date, DayBundle],
    *,
    locale: str,
) -> list[InsightCandidate]:
    paired: list[float] = []
    earlier_values: list[float] = []
    evening_values: list[float] = []
    for day in days.values():
        evening = day.dayparts.get(Daypart.EVENING)
        earlier_scores: list[int] = []
        for part in _EARLIER_DAYPARTS:
            earlier_scores.extend(day.daypart_scores.get(part, ()))
        if evening is None or not earlier_scores:
            continue
        earlier = day_mood_index(earlier_scores)
        paired.append(evening - earlier)
        earlier_values.append(earlier)
        evening_values.append(evening)

    if len(paired) < MIN_PAIRED_DAYS:
        return []
    mean_delta = sum(paired) / len(paired)
    if abs(mean_delta) < MIN_WITHIN_DAY_DELTA:
        return []

    direction = direction_for_delta(mean_delta)
    title_key = (
        "within_day_higher_title"
        if direction is InsightDirection.HIGHER
        else "within_day_lower_title"
    )
    earlier_mean = sum(earlier_values) / len(earlier_values)
    evening_mean = sum(evening_values) / len(evening_values)
    params = {
        "earlier_mood": _fmt_mood(earlier_mean, locale),
        "evening_mood": _fmt_mood(evening_mean, locale),
    }
    # Complement n is the same set: this is a paired mean, not two groups.
    # Reliability still needs two arms; use n vs n so √H = √n.
    return [
        InsightCandidate(
            id=f"within_day:evening:{direction.value}",
            kind=InsightKind.WITHIN_DAY,
            direction=direction,
            strength=strength_for_delta(abs(mean_delta)),
            title=_message(title_key, locale, params),
            body=_message("within_day_body", locale, params),
            sample=_sample_paired(n=len(paired), locale=locale),
            delta=mean_delta,
            lift=None,
            group_mean=evening_mean,
            complement_mean=earlier_mean,
            group_share=None,
            complement_share=None,
            group_n=len(paired),
            complement_n=len(paired),
            subjects=(
                InsightSubject(
                    type=InsightSubjectType.DAYPART,
                    key=Daypart.EVENING.value,
                    label=resolve_label(DAYPART_LABELS[Daypart.EVENING], locale),
                ),
            ),
            reliability=contrast_reliability(
                effect=mean_delta,
                group_n=len(paired),
                complement_n=len(paired),
            ),
        )
    ]


def _tag_mood_candidates(
    days: Mapping[date, DayBundle],
    *,
    tags: Mapping[uuid.UUID, TagRef],
    locale: str,
) -> list[InsightCandidate]:
    results: list[InsightCandidate] = []
    for tag_id, tag in tags.items():
        tagged = [day.day_index for day in days.values() if tag_id in day.tag_ids]
        other = [day.day_index for day in days.values() if tag_id not in day.tag_ids]
        delta = _delta_if_interesting(tagged, other)
        if delta is None:
            continue
        direction = direction_for_delta(delta)
        group_mean = sum(tagged) / len(tagged)
        complement_mean = sum(other) / len(other)
        title_key = (
            "tag_mood_higher_title"
            if direction is InsightDirection.HIGHER
            else "tag_mood_lower_title"
        )
        body_key = (
            "tag_mood_higher_body"
            if direction is InsightDirection.HIGHER
            else "tag_mood_lower_body"
        )
        params = {
            "tag": tag.label,
            **_contrast_params(group_mean, complement_mean, locale),
        }
        results.append(
            InsightCandidate(
                id=f"tag_mood:{tag_id}:{direction.value}",
                kind=InsightKind.TAG_MOOD,
                direction=direction,
                strength=strength_for_delta(abs(delta)),
                title=_message(title_key, locale, params),
                body=_message(body_key, locale, params),
                sample=_sample_tag_mood(
                    tagged_n=len(tagged),
                    other_n=len(other),
                    locale=locale,
                ),
                delta=delta,
                lift=None,
                group_mean=group_mean,
                complement_mean=complement_mean,
                group_share=None,
                complement_share=None,
                group_n=len(tagged),
                complement_n=len(other),
                subjects=(_tag_subject(tag),),
                reliability=contrast_reliability(
                    effect=delta,
                    group_n=len(tagged),
                    complement_n=len(other),
                ),
            )
        )
    return results


def _mood_tag_candidates(
    days: Mapping[date, DayBundle],
    *,
    tags: Mapping[uuid.UUID, TagRef],
    locale: str,
) -> list[InsightCandidate]:
    bundles = list(days.values())
    n_all = len(bundles)
    bright = [day for day in bundles if day.day_index >= HIGH_DAY_INDEX]
    if len(bright) < MIN_HIGH_DAYS or n_all == 0:
        return []

    results: list[InsightCandidate] = []
    n_bright = len(bright)
    for tag_id, tag in tags.items():
        tagged_days = sum(1 for day in bundles if tag_id in day.tag_ids)
        tagged_bright = sum(1 for day in bright if tag_id in day.tag_ids)
        if tagged_days < MIN_GROUP_DAYS:
            continue
        p_tag = tagged_days / n_all
        if p_tag <= 0:
            continue
        p_tag_bright = tagged_bright / n_bright
        lift = p_tag_bright / p_tag
        if lift >= MIN_LIFT:
            if tagged_bright < MIN_TAGGED_HIGH_DAYS:
                continue
            direction = InsightDirection.MORE_OFTEN
        elif lift > 0 and (1.0 / lift) >= MIN_LIFT:
            direction = InsightDirection.LESS_OFTEN
        else:
            continue

        title_key = (
            "mood_tag_more_title"
            if direction is InsightDirection.MORE_OFTEN
            else "mood_tag_less_title"
        )
        body_key = (
            "mood_tag_more_body"
            if direction is InsightDirection.MORE_OFTEN
            else "mood_tag_less_body"
        )
        params = {
            "tag": tag.label,
            "share": _fmt_percent(p_tag_bright),
            "base": _fmt_percent(p_tag),
        }
        results.append(
            InsightCandidate(
                id=f"mood_tag:{tag_id}:{direction.value}",
                kind=InsightKind.MOOD_TAG,
                direction=direction,
                strength=strength_for_lift(lift),
                title=_message(title_key, locale, params),
                body=_message(body_key, locale, params),
                sample=_sample_mood_tag(
                    bright_n=n_bright,
                    tagged_n=tagged_bright,
                    locale=locale,
                ),
                delta=None,
                lift=lift,
                group_mean=None,
                complement_mean=None,
                group_share=p_tag_bright,
                complement_share=p_tag,
                group_n=n_bright,
                complement_n=tagged_days,
                subjects=(_tag_subject(tag),),
                reliability=contrast_reliability(
                    effect=math.log(lift) if lift > 0 else 0.0,
                    group_n=n_bright,
                    complement_n=tagged_days,
                ),
            )
        )
    return results


def _tag_subject(tag: TagRef) -> InsightSubject:
    return InsightSubject(
        type=InsightSubjectType.TAG,
        key=str(tag.id),
        label=tag.label,
        tag=tag,
    )


def _with_focus_boost(item: InsightCandidate, focus: FocusContext) -> InsightCandidate:
    if not _matches_focus(item, focus):
        return item
    return replace(item, reliability=item.reliability * FOCUS_BOOST)


def _matches_focus(item: InsightCandidate, focus: FocusContext) -> bool:
    keys = {subject.key for subject in item.subjects}
    if item.kind is InsightKind.WEEKEND:
        return focus.weekday in _WEEKEND_DAYS
    if item.kind is InsightKind.WEEKDAY:
        return WEEKDAY_KEY.get(focus.weekday) in keys
    if item.kind is InsightKind.DAYPART:
        return focus.daypart.value in keys
    if item.kind is InsightKind.WITHIN_DAY:
        return focus.daypart is Daypart.EVENING
    if item.kind in {InsightKind.TAG_MOOD, InsightKind.MOOD_TAG}:
        return any(
            subject.tag is not None and subject.tag.id in focus.tag_ids for subject in item.subjects
        )
    return False


def _pick_diverse(
    ranked: Sequence[InsightCandidate],
    *,
    limit: int,
) -> list[InsightCandidate]:
    picked: list[InsightCandidate] = []
    used_kinds: set[InsightKind] = set()
    used_tag_ids: set[uuid.UUID] = set()
    for item in ranked:
        if len(picked) >= limit:
            break
        if item.kind in used_kinds:
            continue
        tag_ids = {subject.tag.id for subject in item.subjects if subject.tag is not None}
        if tag_ids & used_tag_ids:
            continue
        picked.append(item)
        used_kinds.add(item.kind)
        used_tag_ids.update(tag_ids)
    return picked


def nearest_mood_score(value: float) -> MoodScore:
    """Map a 1–5 average onto the nearest named mood (round half up).

    Users think in faces, not tenths: 2.8 is ``neutral``, 3.7 is ``good``.
    """
    rounded = int(math.floor(value + 0.5))
    clamped = min(MAX_MOOD_SCORE, max(MIN_MOOD_SCORE, rounded))
    return MoodScore(clamped)


def _fmt_index(value: float) -> str:
    return f"{value:.1f}"


def _fmt_mood(value: float, locale: str) -> str:
    """Inline reading for body copy: ``2.8 (neutral)`` / ``2.8 («нейтрально»)``."""
    return _message(
        "mood_reading",
        locale,
        {
            "label": mood_score_label(nearest_mood_score(value), locale),
            "number": _fmt_index(value),
        },
    )


def _contrast_params(
    group_mean: float,
    complement_mean: float,
    locale: str,
) -> dict[str, object]:
    return {
        "group_mood": _fmt_mood(group_mean, locale),
        "complement_mood": _fmt_mood(complement_mean, locale),
    }


def _fmt_percent(value: float) -> str:
    return f"{round(value * 100):.0f}"


def _message(key: str, locale: str, params: Mapping[str, object]) -> str:
    template = resolve_label(_MESSAGES[key], locale)
    return template.format(**params)


def _cap_first(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def _plural_category(count: int, locale: str) -> str:
    n = abs(count)
    if normalize_locale(locale) == "ru":
        n100 = n % 100
        n10 = n % 10
        if n10 == 1 and n100 != 11:
            return "one"
        if 2 <= n10 <= 4 and not (12 <= n100 <= 14):
            return "few"
        return "many"
    return "one" if n == 1 else "many"


def _counted(forms: Mapping[str, LocaleLabels], count: int, locale: str) -> str:
    category = _plural_category(count, locale)
    labels = forms.get(category) or forms.get("many") or next(iter(forms.values()))
    return resolve_label(labels, locale)


def _daypart_title(
    higher: Daypart,
    lower: Daypart,
    locale: str,
    params: Mapping[str, object],
) -> str:
    if lower is Daypart.EVENING:
        return _message("daypart_dip_evening_title", locale, params)
    if lower is Daypart.NIGHT:
        return _message("daypart_dip_night_title", locale, params)
    return _message("daypart_better_title", locale, params)


def _sample_weekend(*, weekend_n: int, weekday_n: int, locale: str) -> str:
    weekends = _counted(_WEEKEND_DAY_FORMS, weekend_n, locale)
    weekdays = _counted(_WEEKDAY_BAND_FORMS, weekday_n, locale)
    return f"{weekend_n} {weekends} · {weekday_n} {weekdays}"


def _sample_weekday(*, weekday: int, group_n: int, complement_n: int, locale: str) -> str:
    noun = _counted(WEEKDAY_COUNT_FORMS[weekday], group_n, locale)
    other = _counted(_OTHER_DAY_FORMS, complement_n, locale)
    return f"{group_n} {noun} · {complement_n} {other}"


def _sample_daypart(
    *,
    higher: Daypart,
    lower: Daypart,
    higher_n: int,
    lower_n: int,
    locale: str,
) -> str:
    if normalize_locale(locale) == "ru":
        higher_days = _counted(_DAYS_FORMS, higher_n, locale)
        lower_days = _counted(_DAYS_FORMS, lower_n, locale)
        higher_at = resolve_label(DAYPART_LABELS[higher], locale)
        lower_at = resolve_label(DAYPART_LABELS[lower], locale)
        return f"{higher_n} {higher_days} {higher_at} · {lower_n} {lower_days} {lower_at}"
    higher_noun = resolve_label(DAYPART_NOUN_LABELS[higher], locale)
    lower_noun = resolve_label(DAYPART_NOUN_LABELS[lower], locale)
    return f"{higher_n} {higher_noun} · {lower_n} {lower_noun}"


def _sample_paired(*, n: int, locale: str) -> str:
    days = _counted(_DAYS_FORMS, n, locale)
    return _message("sample_paired", locale, {"n": n, "days": days})


def _sample_tag_mood(*, tagged_n: int, other_n: int, locale: str) -> str:
    tagged = _counted(_TAGGED_DAY_FORMS, tagged_n, locale)
    if normalize_locale(locale) == "ru":
        other = _counted(_UNTAGGED_DAY_FORMS, other_n, locale)
        return f"{tagged_n} {tagged} · {other_n} {other}"
    return f"{tagged_n} {tagged} · {other_n} without the tag"


def _sample_mood_tag(*, bright_n: int, tagged_n: int, locale: str) -> str:
    good_days = _counted(_GOOD_DAY_FORMS, bright_n, locale)
    return _message(
        "sample_mood_tag",
        locale,
        {"bright_n": bright_n, "good_days": good_days, "tagged_n": tagged_n},
    )


_DAYS_FORMS: dict[str, LocaleLabels] = {
    "one": {"en": "day", "ru": "день"},
    "few": {"en": "days", "ru": "дня"},
    "many": {"en": "days", "ru": "дней"},
}

_OTHER_DAY_FORMS: dict[str, LocaleLabels] = {
    "one": {"en": "other day", "ru": "остальной день"},
    "few": {"en": "other days", "ru": "остальных дня"},
    "many": {"en": "other days", "ru": "остальных дней"},
}

_WEEKEND_DAY_FORMS: dict[str, LocaleLabels] = {
    "one": {"en": "weekend day", "ru": "выходной"},
    "few": {"en": "weekend days", "ru": "выходных"},
    "many": {"en": "weekend days", "ru": "выходных"},
}

_WEEKDAY_BAND_FORMS: dict[str, LocaleLabels] = {
    "one": {"en": "weekday", "ru": "будний день"},
    "few": {"en": "weekdays", "ru": "будня"},
    "many": {"en": "weekdays", "ru": "будней"},
}

_TAGGED_DAY_FORMS: dict[str, LocaleLabels] = {
    "one": {"en": "tagged day", "ru": "день с тегом"},
    "few": {"en": "tagged days", "ru": "дня с тегом"},
    "many": {"en": "tagged days", "ru": "дней с тегом"},
}

_UNTAGGED_DAY_FORMS: dict[str, LocaleLabels] = {
    "one": {"en": "day without the tag", "ru": "день без него"},
    "few": {"en": "days without the tag", "ru": "дня без него"},
    "many": {"en": "days without the tag", "ru": "дней без него"},
}

_GOOD_DAY_FORMS: dict[str, LocaleLabels] = {
    "one": {"en": "good day", "ru": "хороший день"},
    "few": {"en": "good days", "ru": "хороших дня"},
    "many": {"en": "good days", "ru": "хороших дней"},
}


_MESSAGES: dict[str, LocaleLabels] = {
    "mood_reading": {
        "en": "{number} ({label})",
        "ru": "{number} («{label}»)",
    },
    "weekend_label": {"en": "weekends", "ru": "выходные"},
    "weekdays_label": {"en": "weekdays", "ru": "будни"},
    "weekend_higher_title": {
        "en": "Your mood is usually better on weekends",
        "ru": "По выходным настроение обычно выше",
    },
    "weekend_higher_body": {
        "en": (
            "Your average mood is {group_mood} on weekends, "
            "compared with {complement_mood} on weekdays."
        ),
        "ru": (
            "В субботу и воскресенье среднее настроение — {group_mood}. "
            "В будни — {complement_mood}."
        ),
    },
    "weekend_lower_title": {
        "en": "Your mood is usually lower on weekends",
        "ru": "По выходным настроение обычно ниже",
    },
    "weekend_lower_body": {
        "en": (
            "Your average mood is {group_mood} on weekends, "
            "compared with {complement_mood} on weekdays."
        ),
        "ru": (
            "В субботу и воскресенье среднее настроение — {group_mood}. "
            "В будни — {complement_mood}."
        ),
    },
    "weekday_higher_title": {
        "en": "{weekday} usually feel better",
        "ru": "{weekday} обычно ощущаются лучше",
    },
    "weekday_higher_body": {
        "en": (
            "Your average mood on {weekday_on} is {group_mood}, "
            "compared with {complement_mood} on other days."
        ),
        "ru": (
            "Среднее настроение по {weekday_on} — {group_mood}, "
            "а в остальные дни — {complement_mood}."
        ),
    },
    "weekday_lower_title": {
        "en": "{weekday} tend to be harder",
        "ru": "{weekday} обычно даются тяжелее",
    },
    "weekday_lower_body": {
        "en": (
            "Your average mood on {weekday_on} is {group_mood}, "
            "compared with {complement_mood} on other days."
        ),
        "ru": (
            "Среднее настроение по {weekday_on} — {group_mood}, "
            "а в остальные дни — {complement_mood}."
        ),
    },
    "daypart_dip_evening_title": {
        "en": "Your mood tends to dip by evening",
        "ru": "К вечеру настроение обычно снижается",
    },
    "daypart_dip_night_title": {
        "en": "Your mood tends to dip at night",
        "ru": "К ночи настроение обычно снижается",
    },
    "daypart_better_title": {
        "en": "Your mood is usually better {higher_at}",
        "ru": "{higher_at_cap} настроение обычно лучше",
    },
    "daypart_body": {
        "en": ("Your average mood is {group_mood} {higher_at} and {complement_mood} {lower_at}."),
        "ru": ("Среднее настроение {higher_at} — {group_mood}, {lower_at} — {complement_mood}."),
    },
    "within_day_lower_title": {
        "en": "Your mood tends to dip by evening",
        "ru": "К вечеру настроение обычно снижается",
    },
    "within_day_higher_title": {
        "en": "Your mood tends to lift by evening",
        "ru": "К вечеру настроение обычно становится лучше",
    },
    "within_day_body": {
        "en": (
            "On days with both daytime and evening entries, your average mood is "
            "{earlier_mood} during the day and {evening_mood} in the evening."
        ),
        "ru": (
            "В дни с записями днём и вечером среднее настроение днём — "
            "{earlier_mood}, а вечером — {evening_mood}."
        ),
    },
    "tag_mood_higher_title": {
        "en": "“{tag}” shows up more often on better days",
        "ru": "«{tag}» чаще появляется в более лёгкие дни",
    },
    "tag_mood_higher_body": {
        "en": (
            "Your average mood is {group_mood} on days with this tag, "
            "compared with {complement_mood} on other days."
        ),
        "ru": ("В такие дни среднее настроение — {group_mood}. В остальные — {complement_mood}."),
    },
    "tag_mood_lower_title": {
        "en": "“{tag}” shows up more often on lower-mood days",
        "ru": "«{tag}» чаще появляется в более тяжёлые дни",
    },
    "tag_mood_lower_body": {
        "en": (
            "Your average mood is {group_mood} on days with this tag, "
            "compared with {complement_mood} on other days."
        ),
        "ru": ("В такие дни среднее настроение — {group_mood}. В остальные — {complement_mood}."),
    },
    "mood_tag_more_title": {
        "en": "You mention “{tag}” more on good days",
        "ru": "В хорошие дни ты чаще отмечаешь «{tag}»",
    },
    "mood_tag_more_body": {
        "en": (
            "The tag appears on {share}% of good or great days, "
            "compared with {base}% of days overall."
        ),
        "ru": (
            "Этот тег появляется в {share}% дней с настроением «хорошо» или «отлично». "
            "В целом — в {base}% дней."
        ),
    },
    "mood_tag_less_title": {
        "en": "You mention “{tag}” less on good days",
        "ru": "В хорошие дни ты реже отмечаешь «{tag}»",
    },
    "mood_tag_less_body": {
        "en": (
            "The tag appears on {share}% of good or great days, "
            "compared with {base}% of days overall."
        ),
        "ru": (
            "Этот тег появляется в {share}% дней с настроением «хорошо» или «отлично». "
            "В целом — в {base}% дней."
        ),
    },
    "sample_paired": {
        "en": "{n} {days} with both daytime and evening entries",
        "ru": "{n} {days} с записями днём и вечером",
    },
    "sample_mood_tag": {
        "en": "{bright_n} {good_days} · tag appeared on {tagged_n} of them",
        "ru": "{bright_n} {good_days} · тег отмечен в {tagged_n} из них",
    },
}
