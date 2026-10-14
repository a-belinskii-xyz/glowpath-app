"""Import a guest local diary into the account the guest signed in to."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.goal_tracking import MAX_GOAL_PARTIAL_LABEL_LENGTH, GoalCheckinLevel
from app.core.mood_scale import MoodScore, default_mood_score_style
from app.models.goal import Goal
from app.models.goal_checkin import GoalCheckin
from app.models.guest_device import GuestAuthEvent
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_goal import MoodEntryGoal
from app.models.mood_entry_tag import MoodEntryTag
from app.models.note_template import NoteTemplate
from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.models.user import User
from app.models.user_mood_preferences import UserMoodPreferences
from app.services.achievements.service import evaluate_user_achievements
from app.services.embedding_service import upsert_entry_embedding
from app.services.mood_entry_service import _score_color_for_user, _to_utc
from app.services.visitor_experiment_service import mark_visitor_converted


class GuestImportError(AppError):
    pass


def _sanitize_icon_type(icon_type: str) -> str:
    if icon_type in {"emoji", "builtin"}:
        return icon_type
    return "emoji"


def import_guest_diary(
    db: Session,
    *,
    user: User,
    visitor_id: uuid.UUID,
    payload: dict[str, Any],
) -> dict[str, int]:
    if user.pending_guest_device_id != visitor_id:
        raise GuestImportError(
            "Guest import is not allowed for this account",
            code=ErrorCode.GUEST_IMPORT_NOT_ALLOWED,
            status_code=409,
        )
    if user.guest_imported_at is not None:
        return {"imported_entries": 0, "skipped": True}

    # A fresh account takes the guest's look and onboarding; an account with its own
    # entries keeps its settings and only gains the guest's entries, tags and goals.
    adopt_guest_settings = (
        db.scalar(select(MoodEntry.id).where(MoodEntry.user_id == user.id).limit(1)) is None
    )

    tag_group_map: dict[str, uuid.UUID] = {}
    tag_map: dict[str, uuid.UUID] = {}
    goal_map: dict[str, uuid.UUID] = {}

    existing_groups = {
        group.slug: group
        for group in db.scalars(select(TagGroup).where(TagGroup.user_id == user.id)).all()
    }
    existing_tags = {
        tag.slug: tag for tag in db.scalars(select(Tag).where(Tag.user_id == user.id)).all()
    }
    existing_goals = {
        goal.slug: goal for goal in db.scalars(select(Goal).where(Goal.user_id == user.id)).all()
    }
    existing_templates = {
        template.slug: template
        for template in db.scalars(
            select(NoteTemplate).where(NoteTemplate.user_id == user.id)
        ).all()
    }

    for group_data in payload.get("tag_groups", []):
        slug = str(group_data["slug"])
        if slug in existing_groups:
            tag_group_map[slug] = existing_groups[slug].id
            continue
        group = TagGroup(
            user_id=user.id,
            slug=slug,
            labels=dict(group_data.get("labels", {})),
            sort_order=int(group_data.get("sort_order", 0)),
            show_on_entry=bool(group_data.get("show_on_entry", False)),
        )
        db.add(group)
        db.flush()
        tag_group_map[slug] = group.id
        existing_groups[slug] = group

    for tag_data in payload.get("tags", []):
        slug = str(tag_data["slug"])
        if slug in existing_tags:
            tag_map[slug] = existing_tags[slug].id
            continue
        group_slug = str(tag_data["group_slug"])
        group_id = tag_group_map.get(group_slug)
        if group_id is None:
            continue
        tag = Tag(
            group_id=group_id,
            user_id=user.id,
            slug=slug,
            labels=dict(tag_data.get("labels", {})),
            sort_order=int(tag_data.get("sort_order", 0)),
            color=str(tag_data.get("color", "#94a3b8")),
            icon_type=_sanitize_icon_type(str(tag_data.get("icon_type", "emoji"))),
            icon=str(tag_data.get("icon", "🏷️")),
        )
        db.add(tag)
        db.flush()
        tag_map[slug] = tag.id
        existing_tags[slug] = tag

    for goal_data in payload.get("goals", []):
        slug = str(goal_data["slug"])
        if slug in existing_goals:
            goal_map[slug] = existing_goals[slug].id
            continue
        starts_on_raw = goal_data.get("starts_on")
        starts_on = (
            date.fromisoformat(str(starts_on_raw)) if starts_on_raw else _local_today(user.timezone)
        )
        ends_on_raw = goal_data.get("ends_on")
        ends_on = date.fromisoformat(str(ends_on_raw)) if ends_on_raw else None
        goal = Goal(
            user_id=user.id,
            slug=slug,
            labels=dict(goal_data.get("labels", {})),
            times_per_week=int(goal_data.get("times_per_week", 1)),
            tracking_kind=str(goal_data.get("tracking_kind", "binary")),
            target_amount=goal_data.get("target_amount"),
            unit=goal_data.get("unit"),
            partial_label=_partial_label(goal_data.get("partial_label")),
            starts_on=starts_on,
            ends_on=ends_on,
            sort_order=int(goal_data.get("sort_order", 0)),
            show_on_entry=bool(goal_data.get("show_on_entry", False)),
            show_in_stats=bool(goal_data.get("show_in_stats", False)),
            color=str(goal_data.get("color", "#60a5fa")),
            icon_type=_sanitize_icon_type(str(goal_data.get("icon_type", "emoji"))),
            icon=str(goal_data.get("icon", "🎯")),
        )
        db.add(goal)
        db.flush()
        goal_map[slug] = goal.id
        existing_goals[slug] = goal
    _import_goal_checkins(db, user=user, goals=payload.get("goals", []), goal_map=goal_map)

    for template_data in payload.get("note_templates", []):
        slug = str(template_data["slug"])
        if slug in existing_templates:
            continue
        template = NoteTemplate(
            user_id=user.id,
            slug=slug,
            labels=dict(template_data.get("labels", {})),
            bodies=dict(template_data.get("bodies", {})),
            sort_order=int(template_data.get("sort_order", 0)),
        )
        db.add(template)
        existing_templates[slug] = template

    prefs_data = payload.get("mood_preferences")
    if adopt_guest_settings and isinstance(prefs_data, dict):
        prefs = db.scalar(select(UserMoodPreferences).where(UserMoodPreferences.user_id == user.id))
        if prefs is not None:
            score_styles = prefs_data.get("scores")
            if isinstance(score_styles, dict):
                sanitized: dict[str, dict[str, str]] = {}
                for score_key, style in score_styles.items():
                    if not isinstance(style, dict):
                        continue
                    icon_type = _sanitize_icon_type(str(style.get("icon_type", "emoji")))
                    fallback = default_mood_score_style(MoodScore(int(score_key)))
                    sanitized[str(score_key)] = {
                        "icon_type": icon_type,
                        "icon": str(style.get("icon", fallback.icon)),
                        "color": str(style.get("color", fallback.color)),
                    }
                prefs.score_styles = sanitized
            if "use_historical_colors" in prefs_data:
                prefs.use_historical_colors = bool(prefs_data["use_historical_colors"])
            if "show_streak" in prefs_data:
                prefs.show_streak = bool(prefs_data["show_streak"])
            if "composer_blocks" in prefs_data:
                from app.services.mood_preferences_service import sanitize_composer_blocks

                raw_blocks = prefs_data.get("composer_blocks")
                prefs.composer_blocks = sanitize_composer_blocks(
                    raw_blocks if isinstance(raw_blocks, list) else None
                )

    local_tag_id_map: dict[str, uuid.UUID] = {}
    for tag_data in payload.get("tags", []):
        local_id = str(tag_data.get("local_id", ""))
        slug = str(tag_data["slug"])
        if local_id and slug in tag_map:
            local_tag_id_map[local_id] = tag_map[slug]

    local_goal_id_map: dict[str, uuid.UUID] = {}
    for goal_data in payload.get("goals", []):
        local_id = str(goal_data.get("local_id", ""))
        slug = str(goal_data["slug"])
        if local_id and slug in goal_map:
            local_goal_id_map[local_id] = goal_map[slug]

    imported_entries = 0
    for entry_data in payload.get("entries", []):
        score = int(entry_data["score"])
        recorded_at = datetime.fromisoformat(str(entry_data["recorded_at"]))
        recorded_at_utc = _to_utc(recorded_at)
        entry = MoodEntry(
            user_id=user.id,
            score=score,
            recorded_at=recorded_at_utc,
            note=entry_data.get("note"),
            is_favorite=bool(entry_data.get("is_favorite", False)),
            score_color=_score_color_for_user(db, user_id=user.id, score=score),
        )
        db.add(entry)
        db.flush()

        tag_ids: list[uuid.UUID] = []
        for local_tag_id in entry_data.get("tag_ids", []):
            mapped = local_tag_id_map.get(str(local_tag_id))
            if mapped is not None:
                tag_ids.append(mapped)
        if tag_ids:
            tags = list(
                db.scalars(select(Tag).where(Tag.user_id == user.id, Tag.id.in_(tag_ids))).all()
            )
            for tag in tags:
                entry.tag_links.append(MoodEntryTag(tag_id=tag.id, color=tag.color))

        goal_ids: list[uuid.UUID] = []
        for local_goal_id in entry_data.get("goal_ids", []):
            mapped = local_goal_id_map.get(str(local_goal_id))
            if mapped is not None:
                goal_ids.append(mapped)
        progress_by_goal = {
            str(item["goal_id"]): int(item["amount"])
            for item in entry_data.get("goal_progress", [])
            if isinstance(item, dict) and "goal_id" in item and "amount" in item
        }
        if goal_ids:
            goals = list(
                db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.id.in_(goal_ids))).all()
            )
            for goal in goals:
                local_match = next(
                    (
                        progress_by_goal.get(str(local_id))
                        for local_id, mapped in local_goal_id_map.items()
                        if mapped == goal.id and str(local_id) in progress_by_goal
                    ),
                    progress_by_goal.get(str(goal.id)),
                )
                entry.goal_links.append(
                    MoodEntryGoal(
                        goal_id=goal.id,
                        color=goal.color,
                        amount=local_match,
                    )
                )

        upsert_entry_embedding(db, entry)
        evaluate_user_achievements(db, user=user, source_entry_id=entry.id)
        imported_entries += 1

    meta = payload.get("meta")
    if (
        isinstance(meta, dict)
        and bool(meta.get("onboarding_completed"))
        and user.onboarding_completed_at is None
    ):
        user.onboarding_completed_at = datetime.now(UTC)

    user.guest_imported_at = datetime.now(UTC)
    mark_visitor_converted(
        db,
        visitor_id=visitor_id,
        user_id=user.id,
        auth_event=GuestAuthEvent.IMPORTED,
    )
    db.commit()
    return {"imported_entries": imported_entries, "skipped": False}


def _partial_label(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()[:MAX_GOAL_PARTIAL_LABEL_LENGTH]


def _import_goal_checkins(
    db: Session, *, user: User, goals: list[dict[str, Any]], goal_map: dict[str, uuid.UUID]
) -> None:
    """Carry days the guest marked without an entry (GP-43); days already marked stay as is."""
    taken = {
        (goal_id, day)
        for goal_id, day in db.execute(
            select(GoalCheckin.goal_id, GoalCheckin.day).where(GoalCheckin.user_id == user.id)
        ).all()
    }
    levels = {level.value for level in GoalCheckinLevel}
    for goal_data in goals:
        goal_id = goal_map.get(str(goal_data.get("slug")))
        checkins = goal_data.get("checkins")
        if goal_id is None or not isinstance(checkins, dict):
            continue
        for day_raw, level in checkins.items():
            try:
                day = date.fromisoformat(str(day_raw))
            except ValueError:
                continue
            if level not in levels or (goal_id, day) in taken:
                continue
            taken.add((goal_id, day))
            db.add(GoalCheckin(user_id=user.id, goal_id=goal_id, day=day, level=level))


def _local_today(timezone_name: str) -> date:
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except ZoneInfoNotFoundError:
        return datetime.now(UTC).date()
