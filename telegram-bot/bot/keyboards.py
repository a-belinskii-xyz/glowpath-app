from __future__ import annotations

from typing import Any

from bot.i18n import t


def inline_keyboard(rows: list[list[dict[str, str]]]) -> dict[str, Any]:
    return {"inline_keyboard": rows}


def score_keyboard(scores: list[dict[str, Any]]) -> dict[str, Any]:
    row = [
        {
            "text": f"{item.get('emoji', '')} {item['score']}".strip(),
            "callback_data": f"w:score:{item['score']}",
        }
        for item in scores
    ]
    return inline_keyboard([row])


def tags_keyboard(
    tags: list[dict[str, Any]],
    selected_ids: set[str],
    *,
    locale: str | None,
) -> dict[str, Any]:
    rows: list[list[dict[str, str]]] = []
    for tag in tags:
        tag_id = str(tag["id"])
        mark = "✓ " if tag_id in selected_ids else ""
        rows.append(
            [
                {
                    "text": f"{mark}{tag['label']}",
                    "callback_data": f"w:tag:{tag_id}",
                }
            ]
        )
    rows.append([{"text": t(locale, "next"), "callback_data": "w:next"}])
    return inline_keyboard(rows)


def goals_keyboard(
    goals: list[dict[str, Any]],
    selected_ids: set[str],
    *,
    locale: str | None,
) -> dict[str, Any]:
    rows: list[list[dict[str, str]]] = []
    for goal in goals:
        goal_id = str(goal["id"])
        mark = "✓ " if goal_id in selected_ids else ""
        icon = goal.get("icon") if goal.get("icon_type") == "emoji" else ""
        label = f"{icon} {goal['label']}".strip() if icon else goal["label"]
        rows.append(
            [
                {
                    "text": f"{mark}{label}",
                    "callback_data": f"w:goal:{goal_id}",
                }
            ]
        )
    rows.append(
        [
            {"text": t(locale, "skip"), "callback_data": "w:skip"},
            {"text": t(locale, "next"), "callback_data": "w:next"},
        ]
    )
    return inline_keyboard(rows)


def skip_keyboard(*, locale: str | None) -> dict[str, Any]:
    return inline_keyboard([[{"text": t(locale, "skip"), "callback_data": "w:skip"}]])


def note_keyboard(*, locale: str | None) -> dict[str, Any]:
    return inline_keyboard(
        [
            [
                {"text": t(locale, "skip"), "callback_data": "w:skip"},
                {"text": t(locale, "next"), "callback_data": "w:next"},
            ]
        ]
    )


def confirm_keyboard(*, locale: str | None) -> dict[str, Any]:
    return inline_keyboard(
        [
            [
                {"text": t(locale, "confirm_yes"), "callback_data": "w:confirm"},
                {"text": t(locale, "confirm_no"), "callback_data": "w:cancel"},
            ]
        ]
    )
