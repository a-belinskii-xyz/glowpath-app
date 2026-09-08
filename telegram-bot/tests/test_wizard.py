from __future__ import annotations

from bot.keyboards import (
    START_CREATE,
    linked_home_keyboard,
    mini_app_keyboard,
    with_start_param,
)
from bot.wizard import (
    MAX_PENDING_PHOTOS,
    SOURCE_BOT,
    STEP_CONFIRM,
    STEP_GOALS,
    STEP_NOTE,
    STEP_SCORE,
    STEP_TAGS,
    add_pending_photo,
    advance_after_goals,
    advance_after_note,
    advance_after_score,
    advance_after_tags,
    format_summary,
    has_note_content,
    new_wizard_state,
    parse_callback,
    toggle_id,
)


def test_with_start_param_appends_query() -> None:
    assert with_start_param("https://example.com", None) == "https://example.com"
    assert (
        with_start_param("https://example.com/app", "create")
        == "https://example.com/app?tgWebAppStartParam=create"
    )
    assert (
        with_start_param("https://example.com/app?x=1", "create")
        == "https://example.com/app?x=1&tgWebAppStartParam=create"
    )


def test_mini_app_keyboard_uses_web_app_button() -> None:
    markup = mini_app_keyboard(locale="en", url="https://example.com")
    button = markup["inline_keyboard"][0][0]
    assert button["text"] == "Open App"
    assert button["web_app"] == {"url": "https://example.com"}


def test_mini_app_keyboard_log_mood_includes_start_param() -> None:
    markup = mini_app_keyboard(
        locale="en",
        url="https://example.com",
        start=START_CREATE,
        button_key="log_mood",
    )
    button = markup["inline_keyboard"][0][0]
    assert button["text"] == "Log mood"
    assert button["web_app"] == {"url": "https://example.com?tgWebAppStartParam=create"}


def test_mini_app_keyboard_onboarding_start_param() -> None:
    from bot.keyboards import START_ONBOARDING

    markup = mini_app_keyboard(
        locale="en",
        url="https://example.com",
        start=START_ONBOARDING,
    )
    button = markup["inline_keyboard"][0][0]
    assert button["web_app"]["url"].endswith("tgWebAppStartParam=onboarding")


def test_linked_home_keyboard_has_log_and_open() -> None:
    markup = linked_home_keyboard(locale="en", url="https://example.com")
    rows = markup["inline_keyboard"]
    assert rows[0][0]["text"] == "Log mood"
    assert rows[0][0]["web_app"]["url"].endswith("tgWebAppStartParam=create")
    assert rows[1][0]["web_app"] == {"url": "https://example.com"}


def _catalog(*, tags: bool = True, goals: bool = True, frequent: bool = False) -> dict:
    tag_groups = []
    if tags:
        tag_groups = [
            {
                "id": "g1",
                "label": "Feelings",
                "tags": [
                    {"id": "t1", "label": "Calm"},
                    {"id": "t2", "label": "Tired"},
                ],
            },
            {
                "id": "g2",
                "label": "Context",
                "tags": [{"id": "t3", "label": "Work"}],
            },
        ]
    goal_items = []
    if goals:
        goal_items = [{"id": "goal1", "label": "Exercise", "icon_type": "emoji", "icon": "🏃"}]
    frequent_tags = []
    if frequent:
        frequent_tags = [{"id": "t1", "label": "Calm"}, {"id": "t4", "label": "Coffee"}]
    return {
        "scores": [
            {"score": 1, "label": "awful", "emoji": "😢"},
            {"score": 4, "label": "good", "emoji": "🙂"},
        ],
        "tag_groups": tag_groups,
        "frequent_tags": frequent_tags,
        "goals": goal_items,
    }


def test_new_wizard_state_defaults() -> None:
    state = new_wizard_state()
    assert state["step"] == STEP_SCORE
    assert state["source"] == SOURCE_BOT
    assert state["tag_ids"] == []


def test_advance_score_to_tags_then_goals_then_note() -> None:
    catalog = _catalog()
    state = new_wizard_state()
    state["score"] = 4
    state = advance_after_score(state, catalog)
    assert state["step"] == STEP_TAGS
    assert state["group_index"] == 0

    state = advance_after_tags(state, catalog)
    assert state["step"] == STEP_TAGS
    assert state["group_index"] == 1

    state = advance_after_tags(state, catalog)
    assert state["step"] == STEP_GOALS

    state = advance_after_goals(state)
    assert state["step"] == STEP_NOTE

    state = advance_after_note(state)
    assert state["step"] == STEP_CONFIRM


def test_advance_skips_empty_sections() -> None:
    catalog = _catalog(tags=False, goals=False)
    state = new_wizard_state()
    state["score"] = 3
    state = advance_after_score(state, catalog)
    assert state["step"] == STEP_NOTE


def test_advance_inserts_frequent_tags_before_groups() -> None:
    catalog = _catalog(frequent=True)
    state = new_wizard_state()
    state["score"] = 4
    state = advance_after_score(state, catalog)
    assert state["step"] == STEP_TAGS
    assert state["group_index"] == 0

    state = advance_after_tags(state, catalog)
    assert state["step"] == STEP_TAGS
    assert state["group_index"] == 1

    state = advance_after_tags(state, catalog)
    assert state["step"] == STEP_TAGS
    assert state["group_index"] == 2

    state = advance_after_tags(state, catalog)
    assert state["step"] == STEP_GOALS


def test_format_summary_dedupes_frequent_and_group_tags() -> None:
    catalog = _catalog(frequent=True)
    state = new_wizard_state()
    state["score"] = 4
    state["tag_ids"] = ["t1"]
    summary = format_summary(state, catalog)
    assert summary.count("Calm") == 1


def test_toggle_id() -> None:
    state = new_wizard_state()
    state = toggle_id(state, "tag_ids", "t1")
    assert state["tag_ids"] == ["t1"]
    state = toggle_id(state, "tag_ids", "t1")
    assert state["tag_ids"] == []


def test_format_summary() -> None:
    catalog = _catalog()
    state = new_wizard_state()
    state["score"] = 4
    state["tag_ids"] = ["t1", "t3"]
    state["goal_ids"] = ["goal1"]
    state["note"] = "hello"
    state["pending_voice_file_id"] = "file-1"
    state["pending_photos"] = [{"file_id": "p1", "mime_type": "image/jpeg"}]
    summary = format_summary(state, catalog)
    assert "🙂" in summary
    assert "Calm" in summary
    assert "Work" in summary
    assert "Exercise" in summary
    assert "hello" in summary
    assert "🎤" in summary
    assert "🖼×1" in summary


def test_add_pending_photo_and_limit() -> None:
    state = new_wizard_state()
    for i in range(MAX_PENDING_PHOTOS):
        state, err = add_pending_photo(state, file_id=f"p{i}")
        assert err is None
    assert has_note_content(state)
    state, err = add_pending_photo(state, file_id="overflow")
    assert err == "photo_limit"


def test_parse_callback() -> None:
    assert parse_callback("w:score:4") == ("score", "4")
    assert parse_callback("w:next") == ("next", None)
    assert parse_callback("w:tag:abc-def") == ("tag", "abc-def")
    assert parse_callback("other") == ("", None)
