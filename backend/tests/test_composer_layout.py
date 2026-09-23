"""Mirrors frontend/src/lib/entryComposer.ts resolveComposerLayout rules."""

from __future__ import annotations

from typing import Any

REGISTRY = [
    {"id": "mood", "default_enabled": True, "pinned": True},
    {"id": "note", "default_enabled": True, "pinned": False},
    {"id": "tags", "default_enabled": True, "pinned": False},
    {"id": "goals", "default_enabled": True, "pinned": False},
    {"id": "attachments", "default_enabled": True, "pinned": False},
]


def resolve_composer_layout(saved: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    known = {item["id"]: item for item in REGISTRY}
    order = [item["id"] for item in REGISTRY]

    if not saved:
        return [
            {
                "id": item["id"],
                "enabled": item["default_enabled"],
                "pinned": item["pinned"],
            }
            for item in REGISTRY
        ]

    seen: set[str] = set()
    ordered: list[dict[str, Any]] = []
    for item in saved:
        block_id = item.get("id")
        if not isinstance(block_id, str) or block_id not in known or block_id in seen:
            continue
        seen.add(block_id)
        meta = known[block_id]
        ordered.append(
            {
                "id": block_id,
                "enabled": True if meta["pinned"] else bool(item.get("enabled")),
                "pinned": meta["pinned"],
            }
        )

    for block_id in order:
        if block_id in seen:
            continue
        meta = known[block_id]
        ordered.append(
            {
                "id": block_id,
                "enabled": meta["default_enabled"],
                "pinned": meta["pinned"],
            }
        )

    mood = next(
        (block for block in ordered if block["id"] == "mood"),
        {"id": "mood", "enabled": True, "pinned": True},
    )
    rest = [block for block in ordered if block["id"] != "mood"]
    return [{**mood, "enabled": True, "pinned": True}, *rest]


def test_resolve_defaults_when_null() -> None:
    assert [block["id"] for block in resolve_composer_layout(None)] == [
        "mood",
        "note",
        "tags",
        "goals",
        "attachments",
    ]
    assert all(block["enabled"] for block in resolve_composer_layout(None))


def test_resolve_pins_mood_first_and_enabled() -> None:
    layout = resolve_composer_layout(
        [
            {"id": "tags", "enabled": True},
            {"id": "mood", "enabled": False},
            {"id": "note", "enabled": False},
        ]
    )
    assert layout[0] == {"id": "mood", "enabled": True, "pinned": True}
    assert layout[1]["id"] == "tags"
    assert layout[2] == {"id": "note", "enabled": False, "pinned": False}


def test_resolve_drops_unknown_and_appends_missing() -> None:
    layout = resolve_composer_layout(
        [
            {"id": "mood", "enabled": True},
            {"id": "garbage", "enabled": True},
            {"id": "attachments", "enabled": False},
        ]
    )
    ids = [block["id"] for block in layout]
    assert "garbage" not in ids
    assert ids == ["mood", "attachments", "note", "tags", "goals"]
    assert layout[1]["enabled"] is False
    assert layout[2]["enabled"] is True


def test_resolve_dedupes_ids() -> None:
    layout = resolve_composer_layout(
        [
            {"id": "mood", "enabled": True},
            {"id": "note", "enabled": False},
            {"id": "note", "enabled": True},
        ]
    )
    assert [block["id"] for block in layout].count("note") == 1
    assert next(block for block in layout if block["id"] == "note")["enabled"] is False
