from __future__ import annotations

from typing import Any

STEP_SCORE = "choose_score"
STEP_TAGS = "choose_tags"
STEP_GOALS = "choose_goals"
STEP_NOTE = "note_or_voice"
STEP_CONFIRM = "confirm"

SOURCE_BOT = "telegram:bot"
SOURCE_DAILY = "telegram:daily_mood_reminder"
FREQUENT_TAGS_GROUP_SLUG = "frequent_week"

# Match backend mood_entry_service / MoodEntryAttachment limits.
MAX_PENDING_PHOTOS = 5


def new_wizard_state(*, source: str = SOURCE_BOT) -> dict[str, Any]:
    return {
        "step": STEP_SCORE,
        "source": source,
        "score": None,
        "tag_ids": [],
        "goal_ids": [],
        "note": None,
        "group_index": 0,
        "pending_voice_file_id": None,
        "pending_voice_mime": None,
        "pending_photos": [],
    }


def pending_photos(state: dict[str, Any]) -> list[dict[str, Any]]:
    raw = state.get("pending_photos") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict) and isinstance(item.get("file_id"), str)]


def has_note_content(state: dict[str, Any]) -> bool:
    note = state.get("note")
    if isinstance(note, str) and note.strip():
        return True
    if state.get("pending_voice_file_id"):
        return True
    return bool(pending_photos(state))


def add_pending_photo(
    state: dict[str, Any],
    *,
    file_id: str,
    mime_type: str = "image/jpeg",
) -> tuple[dict[str, Any], str | None]:
    """Append a photo. Returns (state, error_key) where error_key is an i18n key or None."""
    photos = pending_photos(state)
    if len(photos) >= MAX_PENDING_PHOTOS:
        return state, "photo_limit"
    next_state = dict(state)
    next_state["pending_photos"] = [
        *photos,
        {"file_id": file_id, "mime_type": mime_type or "image/jpeg"},
    ]
    return next_state, None


def selected_set(state: dict[str, Any], key: str) -> set[str]:
    raw = state.get(key) or []
    return {str(item) for item in raw}


def toggle_id(state: dict[str, Any], key: str, item_id: str) -> dict[str, Any]:
    selected = selected_set(state, key)
    if item_id in selected:
        selected.remove(item_id)
    else:
        selected.add(item_id)
    next_state = dict(state)
    next_state[key] = sorted(selected)
    return next_state


def entry_groups(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    groups = list(catalog.get("tag_groups") or [])
    frequent = list(catalog.get("frequent_tags") or [])
    if frequent:
        groups = [
            {
                "id": FREQUENT_TAGS_GROUP_SLUG,
                "slug": FREQUENT_TAGS_GROUP_SLUG,
                "label": FREQUENT_TAGS_GROUP_SLUG,
                "tags": frequent,
            },
            *groups,
        ]
    return groups


def entry_goals(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    return list(catalog.get("goals") or [])


def advance_after_score(state: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    next_state = dict(state)
    groups = entry_groups(catalog)
    if groups:
        next_state["step"] = STEP_TAGS
        next_state["group_index"] = 0
        return next_state
    return advance_after_tags(next_state, catalog)


def advance_after_tags(state: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    next_state = dict(state)
    groups = entry_groups(catalog)
    index = int(next_state.get("group_index") or 0) + 1
    if index < len(groups):
        next_state["step"] = STEP_TAGS
        next_state["group_index"] = index
        return next_state
    if entry_goals(catalog):
        next_state["step"] = STEP_GOALS
        return next_state
    next_state["step"] = STEP_NOTE
    return next_state


def advance_after_goals(state: dict[str, Any]) -> dict[str, Any]:
    next_state = dict(state)
    next_state["step"] = STEP_NOTE
    return next_state


def advance_after_note(state: dict[str, Any]) -> dict[str, Any]:
    next_state = dict(state)
    next_state["step"] = STEP_CONFIRM
    return next_state


def format_summary(state: dict[str, Any], catalog: dict[str, Any]) -> str:
    score = state.get("score")
    scores = {int(item["score"]): item for item in catalog.get("scores") or []}
    score_meta = scores.get(int(score)) if score is not None else None
    if score_meta:
        score_part = f"{score_meta.get('emoji', '')} {score_meta.get('label', score)}".strip()
    else:
        score_part = str(score)

    tag_labels: list[str] = []
    selected_tags = selected_set(state, "tag_ids")
    seen_tags: set[str] = set()
    for group in entry_groups(catalog):
        for tag in group.get("tags") or []:
            tag_id = str(tag["id"])
            if tag_id in selected_tags and tag_id not in seen_tags:
                seen_tags.add(tag_id)
                tag_labels.append(str(tag["label"]))

    goal_labels: list[str] = []
    selected_goals = selected_set(state, "goal_ids")
    for goal in entry_goals(catalog):
        if str(goal["id"]) in selected_goals:
            goal_labels.append(str(goal["label"]))

    parts = [score_part]
    if tag_labels:
        parts.append(", ".join(tag_labels))
    if goal_labels:
        parts.append(", ".join(goal_labels))
    note = state.get("note")
    if isinstance(note, str) and note.strip():
        parts.append(f"“{note.strip()}”")
    if state.get("pending_voice_file_id"):
        parts.append("🎤")
    photos = pending_photos(state)
    if photos:
        parts.append(f"🖼×{len(photos)}")
    return " · ".join(parts)


def parse_callback(data: str) -> tuple[str, str | None]:
    """Return (action, payload) for wizard callbacks like ``w:score:3``."""
    if not data.startswith("w:"):
        return "", None
    parts = data.split(":", 2)
    if len(parts) == 2:
        return parts[1], None
    if len(parts) >= 3:
        return parts[1], parts[2]
    return "", None
