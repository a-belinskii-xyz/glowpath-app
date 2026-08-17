from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.attachment_kind import AttachmentKind
from app.core.mood_scale import DEFAULT_MOOD_SCORE_COLORS, MoodScore
from app.models.goal import Goal
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_attachment import MoodEntryAttachment
from app.models.mood_entry_goal import MoodEntryGoal
from app.models.mood_entry_tag import MoodEntryTag
from app.models.tag import Tag
from app.services.storage import ObjectStorage
from sqlalchemy.orm import Session

from dev_seed.config import MAX_PHOTOS_PER_ENTRY
from dev_seed.logging_styles import LoggingStyle
from dev_seed.media import tiny_png, tiny_wav
from dev_seed.notes import NOTES, weighted_score
from dev_seed.personas import Persona
from dev_seed.rng import SeededRNG

_UNSAFE_FILENAME_RE = re.compile(r"[^\w.\-]+", re.UNICODE)


@dataclass(slots=True)
class PendingUpload:
    key: str
    data: bytes
    content_type: str


def _safe_filename(name: str) -> str:
    cleaned = _UNSAFE_FILENAME_RE.sub("_", name.strip()).strip("._")
    if not cleaned:
        return "file"
    return cleaned[:200]


def _build_storage_key(
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    attachment_id: uuid.UUID,
    original_name: str,
) -> str:
    return f"{user_id}/{entry_id}/{attachment_id}_{_safe_filename(original_name)}"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _day_log_chance(
    style: LoggingStyle,
    *,
    day: date,
    logged_yesterday: bool | None,
) -> float:
    chance = style.day_chance
    if day.weekday() >= 5:
        chance += style.weekend_delta
    iso_week = day.isocalendar().week
    chance *= style.odd_week_factor if iso_week % 2 else style.even_week_factor
    if logged_yesterday is True:
        chance += style.streak_bonus
    elif logged_yesterday is False:
        chance += style.gap_bonus
    return _clamp(chance, 0.02, 0.92)


def _goal_completion_chance(goal: Goal, style: LoggingStyle) -> float:
    """Probability a logged day counts the goal as done, tuned to times_per_week."""
    weekly_rate = goal.times_per_week / 7.0
    # Consistent loggers hit targets more often; sparse ones miss more.
    adherence = 0.55 + style.day_chance
    return _clamp(weekly_rate * adherence, 0.08, 0.92)


def _pick_note(persona: Persona, rng: SeededRNG) -> str | None:
    if rng.chance(persona.logging.note_skip_chance):
        return None
    pool = NOTES.get(persona.note_flavor, NOTES["calm"])
    locale_notes = pool.get(persona.note_locale) or pool.get("en") or ()
    if not locale_notes:
        return None
    return rng.choice(locale_notes)


def _entry_local_datetime(
    *,
    day: date,
    tz: ZoneInfo,
    rng: SeededRNG,
) -> datetime:
    hour = rng.randint(6, 22)
    minute = rng.choice([0, 5, 10, 15, 20, 30, 40, 45, 50])
    local = datetime.combine(day, time(hour=hour, minute=minute), tzinfo=tz)
    return local.astimezone(UTC)


def create_entries_for_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    persona: Persona,
    tags: list[Tag],
    goals: list[Goal],
    rng: SeededRNG,
    days: int,
    entries_per_day_min: int | None,
    entries_per_day_max: int | None,
    storage: ObjectStorage,
) -> tuple[int, int]:
    """Returns (entry_count, attachment_count). Uploads media after flush."""
    style = persona.logging
    entries_min = entries_per_day_min if entries_per_day_min is not None else style.entries_min
    entries_max = entries_per_day_max if entries_per_day_max is not None else style.entries_max
    if entries_min < 1 or entries_max < entries_min:
        raise ValueError("Invalid entries-per-day range")

    tz = ZoneInfo(persona.timezone)
    today = datetime.now(tz).date()
    entry_count = 0
    attachment_count = 0
    pending: list[PendingUpload] = []
    logged_yesterday: bool | None = None
    tags_sorted = sorted(tags, key=lambda t: (t.slug, str(t.labels)))
    goals_sorted = sorted(goals, key=lambda g: (g.sort_order, g.slug))

    # Iterate oldest → newest so streak/gap momentum matches calendar time.
    for day_offset in range(days - 1, -1, -1):
        day = today - timedelta(days=day_offset)
        chance = _day_log_chance(style, day=day, logged_yesterday=logged_yesterday)
        if not rng.chance(chance):
            logged_yesterday = False
            continue

        n_entries = rng.randint(entries_min, entries_max)
        used_minutes: set[tuple[int, int]] = set()
        active_goals = [
            goal
            for goal in goals_sorted
            if goal.starts_on <= day and (goal.ends_on is None or goal.ends_on >= day)
        ]
        completed_goal_ids = [
            goal.id
            for goal in active_goals
            if rng.chance(_goal_completion_chance(goal, style))
        ]

        for entry_index in range(n_entries):
            entry_key = f"{persona.key}:{day.isoformat()}:{entry_index}"
            entry_id = rng.uuid("entry", entry_key)

            recorded_at = _entry_local_datetime(day=day, tz=tz, rng=rng)
            for _ in range(19):
                stamp = (recorded_at.astimezone(tz).hour, recorded_at.astimezone(tz).minute)
                if stamp not in used_minutes:
                    used_minutes.add(stamp)
                    break
                recorded_at = _entry_local_datetime(day=day, tz=tz, rng=rng)
            else:
                used_minutes.add(
                    (recorded_at.astimezone(tz).hour, recorded_at.astimezone(tz).minute)
                )

            note = _pick_note(persona, rng)
            score = weighted_score(rng.random())

            entry = MoodEntry(
                id=entry_id,
                user_id=user_id,
                recorded_at=recorded_at,
                score=score,
                score_color=DEFAULT_MOOD_SCORE_COLORS[MoodScore(score)],
                note=note,
            )
            db.add(entry)
            db.flush()

            tag_pick_count = rng.randint(0, min(4, len(tags_sorted)))
            for tag in rng.sample(tags_sorted, tag_pick_count):
                entry.tag_links.append(MoodEntryTag(tag_id=tag.id, color=tag.color))

            # Mark day's completed goals on the first entry only (week stats count unique days).
            if entry_index == 0:
                goals_by_id = {goal.id: goal for goal in active_goals}
                for goal_id in completed_goal_ids:
                    goal = goals_by_id[goal_id]
                    entry.goal_links.append(MoodEntryGoal(goal_id=goal_id, color=goal.color))

            if rng.chance(style.photo_chance):
                n_photos = rng.randint(1, MAX_PHOTOS_PER_ENTRY)
                for position in range(1, n_photos + 1):
                    att_id = rng.uuid("attachment", f"{entry_key}:photo:{position}")
                    original_name = f"mood_{day.isoformat()}_{position}.png"
                    r = rng.randint(40, 220)
                    g = rng.randint(40, 220)
                    b = rng.randint(40, 220)
                    data = tiny_png(rgb=(r, g, b))
                    storage_key = _build_storage_key(
                        user_id=user_id,
                        entry_id=entry_id,
                        attachment_id=att_id,
                        original_name=original_name,
                    )
                    db.add(
                        MoodEntryAttachment(
                            id=att_id,
                            mood_entry_id=entry_id,
                            kind=AttachmentKind.PHOTO,
                            storage_key=storage_key,
                            mime_type="image/png",
                            size_bytes=len(data),
                            original_name=original_name,
                            position=position,
                        )
                    )
                    pending.append(
                        PendingUpload(key=storage_key, data=data, content_type="image/png")
                    )
                    attachment_count += 1

            if rng.chance(style.audio_chance):
                att_id = rng.uuid("attachment", f"{entry_key}:audio")
                original_name = f"voice_{day.isoformat()}.wav"
                freq = rng.choice([220, 330, 440, 550, 660])
                data = tiny_wav(frequency_hz=freq, duration_ms=rng.randint(60, 120))
                storage_key = _build_storage_key(
                    user_id=user_id,
                    entry_id=entry_id,
                    attachment_id=att_id,
                    original_name=original_name,
                )
                db.add(
                    MoodEntryAttachment(
                        id=att_id,
                        mood_entry_id=entry_id,
                        kind=AttachmentKind.AUDIO,
                        storage_key=storage_key,
                        mime_type="audio/wav",
                        size_bytes=len(data),
                        original_name=original_name,
                        position=None,
                    )
                )
                pending.append(PendingUpload(key=storage_key, data=data, content_type="audio/wav"))
                attachment_count += 1

            entry_count += 1

        logged_yesterday = True

    db.flush()
    for item in pending:
        storage.put_object(key=item.key, data=item.data, content_type=item.content_type)

    return entry_count, attachment_count
