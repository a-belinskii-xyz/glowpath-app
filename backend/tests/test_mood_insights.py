"""Unit tests for pattern-insight formulas and thresholds."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.core.mood_insights import (
    FOCUS_BOOST,
    HIGH_DAY_INDEX,
    INSIGHT_DEFAULT_LOOKBACK_DAYS,
    MIN_ACTIVE_DAYS_FOR_INSIGHTS,
    MIN_INTERESTING_DELTA,
    Daypart,
    FocusContext,
    InsightDirection,
    InsightKind,
    MoodObservation,
    TagRef,
    _mood_tag_candidates,
    build_insights,
    bundle_days,
    contrast_reliability,
    daypart_for_hour,
    nearest_mood_score,
)
from app.core.mood_scale import MoodScore


def _at(day: date, hour: int) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)


def _obs(
    day: date,
    score: int,
    *,
    hour: int = 12,
    tags: frozenset[UUID] | None = None,
) -> MoodObservation:
    return MoodObservation(
        local_date=day,
        weekday=day.weekday(),
        hour=hour,
        daypart=daypart_for_hour(hour),
        score=score,
        tag_ids=tags or frozenset(),
        recorded_at=_at(day, hour),
    )


def _span(start: date, days: int) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(days)]


def test_daypart_boundaries() -> None:
    assert daypart_for_hour(5) is Daypart.MORNING
    assert daypart_for_hour(11) is Daypart.MORNING
    assert daypart_for_hour(12) is Daypart.AFTERNOON
    assert daypart_for_hour(16) is Daypart.AFTERNOON
    assert daypart_for_hour(17) is Daypart.EVENING
    assert daypart_for_hour(21) is Daypart.EVENING
    assert daypart_for_hour(22) is Daypart.NIGHT
    assert daypart_for_hour(4) is Daypart.NIGHT


def test_reliability_penalizes_tiny_minority_arm() -> None:
    even = contrast_reliability(effect=0.8, group_n=8, complement_n=8)
    spike = contrast_reliability(effect=0.8, group_n=2, complement_n=40)
    assert even > spike


def test_too_few_active_days_yields_nothing() -> None:
    start = date(2026, 6, 1)
    observations = [_obs(day, 5 if day.weekday() >= 5 else 3) for day in _span(start, 7)]
    assert len({item.local_date for item in observations}) < MIN_ACTIVE_DAYS_FOR_INSIGHTS
    assert build_insights(observations, tags={}, locale="en") == []


def test_weekend_higher_than_weekdays() -> None:
    # 8 weeks from a Monday: weekends 5, weekdays 3.
    start = date(2026, 6, 1)  # Monday
    observations = [_obs(day, 5 if day.weekday() >= 5 else 3) for day in _span(start, 56)]
    items = build_insights(observations, tags={}, locale="en", limit=4)
    weekend = next(item for item in items if item.kind is InsightKind.WEEKEND)
    assert weekend.direction is InsightDirection.HIGHER
    assert weekend.delta is not None
    assert weekend.delta >= MIN_INTERESTING_DELTA
    assert "weekend" in weekend.title.lower()
    assert weekend.group_mean == 5.0
    assert weekend.complement_mean == 3.0
    assert "5.0 (great)" in weekend.body
    assert "3.0 (neutral)" in weekend.body
    assert "1–5" not in weekend.body
    assert "around" not in weekend.body.lower()
    assert " vs " not in weekend.body.lower()
    assert "·" in weekend.sample
    assert "vs" not in weekend.sample.lower()


def test_weekend_message_is_localized() -> None:
    start = date(2026, 6, 1)
    observations = [_obs(day, 5 if day.weekday() >= 5 else 3) for day in _span(start, 56)]
    items = build_insights(observations, tags={}, locale="ru")
    weekend = next(item for item in items if item.kind is InsightKind.WEEKEND)
    assert "выходн" in weekend.title.lower()
    assert "5.0 («отлично»)" in weekend.body
    assert "3.0 («нейтрально»)" in weekend.body
    assert "шкале" not in weekend.body
    assert "около" not in weekend.body
    assert "против" not in weekend.body
    assert "против" not in weekend.sample


def test_quiet_when_days_are_flat() -> None:
    start = date(2026, 6, 1)
    observations = [_obs(day, 3) for day in _span(start, 28)]
    assert build_insights(observations, tags={}, locale="en") == []


def test_afternoon_higher_than_evening() -> None:
    start = date(2026, 6, 1)
    observations: list[MoodObservation] = []
    for day in _span(start, 16):
        observations.append(_obs(day, 5, hour=14))
        observations.append(_obs(day, 2, hour=20))
    items = build_insights(observations, tags={}, locale="en")
    daypart = next(item for item in items if item.kind is InsightKind.DAYPART)
    assert daypart.direction is InsightDirection.HIGHER
    keys = {subject.key for subject in daypart.subjects}
    assert "afternoon" in keys
    assert "evening" in keys
    assert daypart.delta is not None
    assert daypart.delta >= MIN_INTERESTING_DELTA
    assert "dip by evening" in daypart.title.lower()
    assert "5.0 (great)" in daypart.body
    assert "2.0 (bad)" in daypart.body
    assert "vs" not in daypart.title.lower()
    assert " vs " not in daypart.body.lower()
    assert "1–5" not in daypart.body


def test_within_day_evening_dip() -> None:
    start = date(2026, 6, 1)
    observations: list[MoodObservation] = []
    for day in _span(start, 12):
        observations.append(_obs(day, 5, hour=10))
        observations.append(_obs(day, 2, hour=19))
    items = build_insights(observations, tags={}, locale="en")
    within = next(item for item in items if item.kind is InsightKind.WITHIN_DAY)
    assert within.direction is InsightDirection.LOWER
    assert within.delta is not None
    assert within.delta < 0
    assert "dip by evening" in within.title.lower()
    assert "5.0 (great)" in within.body
    assert "2.0 (bad)" in within.body
    assert "1–5" not in within.body
    assert "during the day" in within.body
    assert within.group_mean == 2.0
    assert within.complement_mean == 5.0
    assert "daytime and evening" in within.sample


def test_tag_days_sit_higher() -> None:
    walk = uuid4()
    tag = TagRef(
        id=walk,
        slug="walk",
        label="Walk",
        color="#34d399",
        icon_type="emoji",
        icon="🚶",
    )
    start = date(2026, 6, 1)
    observations: list[MoodObservation] = []
    for index, day in enumerate(_span(start, 16)):
        if index % 2 == 0:
            observations.append(_obs(day, 5, tags=frozenset({walk})))
        else:
            observations.append(_obs(day, 3))
    items = build_insights(observations, tags={walk: tag}, locale="en")
    tagged = next(item for item in items if item.kind is InsightKind.TAG_MOOD)
    assert tagged.direction is InsightDirection.HIGHER
    assert tagged.subjects[0].tag is not None
    assert tagged.subjects[0].tag.slug == "walk"
    assert "Walk" in tagged.title
    assert "shows up more often on better days" in tagged.title
    assert "sit higher" not in tagged.title.lower()
    assert "5.0 (great)" in tagged.body
    assert "3.0 (neutral)" in tagged.body
    assert "1–5" not in tagged.body
    assert "tagged days" in tagged.sample
    assert "without the tag" in tagged.sample
    assert " vs " not in tagged.sample.lower()


def test_when_happy_tag_appears_more_often() -> None:
    social = uuid4()
    tag = TagRef(
        id=social,
        slug="social",
        label="Socializing",
        color="#60a5fa",
        icon_type="emoji",
        icon="💬",
    )
    start = date(2026, 6, 1)
    observations: list[MoodObservation] = []
    # 8 bright tagged days + 8 low untagged days → lift is large.
    for index, day in enumerate(_span(start, 16)):
        if index < 8:
            observations.append(_obs(day, 5, tags=frozenset({social})))
        else:
            observations.append(_obs(day, 2))

    candidates = _mood_tag_candidates(
        bundle_days(observations),
        tags={social: tag},
        locale="en",
    )
    mood_tag = next(item for item in candidates if item.kind is InsightKind.MOOD_TAG)
    assert mood_tag.direction is InsightDirection.MORE_OFTEN
    assert mood_tag.lift is not None
    assert mood_tag.lift == 2.0
    assert mood_tag.group_share == 1.0
    assert abs((mood_tag.complement_share or 0) - 0.5) < 1e-9
    assert mood_tag.title == "You mention “Socializing” more on good days"
    assert "100%" in mood_tag.body
    assert "50%" in mood_tag.body
    assert " vs " not in mood_tag.body.lower()
    assert "×" not in mood_tag.body
    assert "tag appeared on 8 of them" in mood_tag.sample

    # Diversity keeps one card per tag, so the public list may pick tag_mood
    # (same story: tagged days sit higher) instead of the lift card.
    items = build_insights(observations, tags={social: tag}, locale="en")
    linked = [
        item
        for item in items
        if any(subject.tag is not None and subject.tag.id == social for subject in item.subjects)
    ]
    assert linked


def test_diversity_keeps_one_card_per_kind() -> None:
    walk = uuid4()
    sport = uuid4()
    tags = {
        walk: TagRef(walk, "walk", "Walk", "#34d399", "emoji", "🚶"),
        sport: TagRef(sport, "sport", "Sport", "#34d399", "emoji", "🏃"),
    }
    start = date(2026, 6, 1)
    observations: list[MoodObservation] = []
    for index, day in enumerate(_span(start, 24)):
        weekend = day.weekday() >= 5
        score = 5 if weekend else 3
        extra_tags = frozenset({walk, sport}) if index % 2 == 0 else frozenset()
        observations.append(_obs(day, score, tags=extra_tags))
    items = build_insights(observations, tags=tags, locale="en", limit=8)
    kinds = [item.kind for item in items]
    assert len(kinds) == len(set(kinds))


def test_focus_boost_reorders_matching_card() -> None:
    walk = uuid4()
    tag = TagRef(walk, "walk", "Walk", "#34d399", "emoji", "🚶")
    start = date(2026, 6, 1)
    observations: list[MoodObservation] = []
    for index, day in enumerate(_span(start, 28)):
        weekend = day.weekday() >= 5
        score = 5 if weekend else 3
        tags = frozenset({walk}) if index % 3 == 0 else frozenset()
        if tags:
            score = 5
        observations.append(_obs(day, score, tags=tags))

    plain = build_insights(observations, tags={walk: tag}, locale="en", limit=4)
    focused = build_insights(
        observations,
        tags={walk: tag},
        locale="en",
        limit=4,
        focus=FocusContext(weekday=0, daypart=Daypart.AFTERNOON, tag_ids=frozenset({walk})),
    )
    tagged = next(item for item in focused if item.kind is InsightKind.TAG_MOOD)
    plain_tagged = next((item for item in plain if item.kind is InsightKind.TAG_MOOD), None)
    assert tagged.reliability > (plain_tagged.reliability if plain_tagged else 0)
    assert tagged.reliability > 0
    # Boost is exactly FOCUS_BOOST on a matching card.
    if plain_tagged is not None:
        assert tagged.reliability == plain_tagged.reliability * FOCUS_BOOST


def test_russian_copy_avoids_report_voice() -> None:
    walk = uuid4()
    tag = TagRef(walk, "walk", "Отдых", "#34d399", "emoji", "🛋️")
    start = date(2026, 6, 1)
    observations: list[MoodObservation] = []
    for index, day in enumerate(_span(start, 16)):
        if index % 2 == 0:
            observations.append(_obs(day, 2, tags=frozenset({walk})))
        else:
            observations.append(_obs(day, 3))
    items = build_insights(observations, tags={walk: tag}, locale="ru")
    tagged = next(item for item in items if item.kind is InsightKind.TAG_MOOD)
    assert tagged.direction is InsightDirection.LOWER
    assert tagged.title == "«Отдых» чаще появляется в более тяжёлые дни"
    assert "2.0 («плохо»)" in tagged.body
    assert "3.0 («нейтрально»)" in tagged.body
    assert "В дни с" not in tagged.title
    assert "против" not in tagged.body
    assert "против" not in tagged.sample
    assert "шкале" not in tagged.body
    assert "дня с тегом" in tagged.sample or "дней с тегом" in tagged.sample


def test_weekday_copy_is_an_observation() -> None:
    start = date(2026, 6, 1)  # Monday
    observations: list[MoodObservation] = []
    for day in _span(start, 28):
        score = 5 if day.weekday() == 4 else 3
        observations.append(_obs(day, score))
    items = build_insights(observations, tags={}, locale="en")
    friday = next(item for item in items if item.kind is InsightKind.WEEKDAY)
    assert friday.direction is InsightDirection.HIGHER
    assert friday.title == "Fridays usually feel better"
    assert "3.0 (neutral)" in friday.body
    assert "5.0 (great)" in friday.body
    assert "runs higher" not in friday.title.lower()
    assert "Fridays" in friday.sample
    assert "other days" in friday.sample
    ru = build_insights(observations, tags={}, locale="ru")
    friday_ru = next(item for item in ru if item.kind is InsightKind.WEEKDAY)
    assert friday_ru.title == "Пятницы обычно ощущаются лучше"
    assert "по пятницам" in friday_ru.body
    assert "против" not in friday_ru.sample


def test_high_day_threshold_matches_good() -> None:
    assert HIGH_DAY_INDEX == 4.0


def test_nearest_mood_score_round_half_up() -> None:
    assert nearest_mood_score(1.0) is MoodScore.AWFUL
    assert nearest_mood_score(2.4) is MoodScore.BAD
    assert nearest_mood_score(2.5) is MoodScore.NEUTRAL
    assert nearest_mood_score(2.8) is MoodScore.NEUTRAL
    assert nearest_mood_score(3.7) is MoodScore.GOOD
    assert nearest_mood_score(5.0) is MoodScore.GREAT


def test_default_insight_window_ends_at_tomorrow_local() -> None:
    from app.services.mood_insight_service import resolve_insight_window

    now = datetime(2026, 8, 19, 15, 0, tzinfo=UTC)
    window_from, window_to = resolve_insight_window(
        timezone_name="Europe/Minsk",
        recorded_from=None,
        recorded_to=None,
        now=now,
    )
    tz = ZoneInfo("Europe/Minsk")
    end_local = datetime(2026, 8, 20, tzinfo=tz)
    start_local = end_local - timedelta(days=INSIGHT_DEFAULT_LOOKBACK_DAYS)
    assert window_to == end_local.astimezone(UTC)
    assert window_from == start_local.astimezone(UTC)
