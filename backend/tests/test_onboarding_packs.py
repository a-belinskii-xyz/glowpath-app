from app.core.onboarding_packs import (
    BASE_PACK_ID,
    compose_additive_suggestions,
    compose_for_options,
    compose_packs,
    load_onboarding_catalog,
    resolve_pack_ids,
)


def test_catalog_loads_base_and_questions() -> None:
    catalog = load_onboarding_catalog()
    assert BASE_PACK_ID in catalog.packs
    assert len(catalog.questions) == 3
    assert len(catalog.packs) >= 20


def test_skip_resolves_to_base_only() -> None:
    pack_ids = resolve_pack_ids(option_keys=None, skip=True)
    assert pack_ids == (BASE_PACK_ID,)


def test_compose_office_gaming_includes_expected_groups() -> None:
    composed = compose_for_options(
        option_keys=["life.office", "focus.stress", "interest.gaming"],
        skip=False,
    )
    group_slugs = {group.slug for group in composed.tag_groups}
    assert "mood" in group_slugs
    assert "sleep_quality" in group_slugs
    assert "work_context" in group_slugs
    assert "gaming" in group_slugs
    visible = {group.slug for group in composed.tag_groups if group.show_on_entry}
    assert "mood" in visible
    assert "sleep_quality" in visible
    assert "work_context" in visible
    assert "gaming" in visible
    assert len(visible) <= 6


def test_additive_suggestions_exclude_base_and_goals() -> None:
    suggestions = compose_additive_suggestions(
        option_keys=["life.office", "focus.stress", "interest.gaming"]
    )
    group_slugs = {group.slug for group in suggestions.tag_groups}
    assert "work_context" in group_slugs
    assert "gaming" in group_slugs
    assert "mood" not in group_slugs
    assert "weather" not in group_slugs
    assert suggestions.note_templates


def test_dedupe_goal_slug_across_packs() -> None:
    composed = compose_packs(
        resolve_pack_ids(
            option_keys=["life.office", "focus.stress", "focus.emotions", "interest.reading"],
            skip=False,
        )
    )
    goal_slugs = [goal.slug for goal in composed.goals]
    assert len(goal_slugs) == len(set(goal_slugs))


def test_unknown_option_raises() -> None:
    try:
        resolve_pack_ids(option_keys=["life.unknown"], skip=False)
    except ValueError as exc:
        assert "Unknown onboarding options" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_missing_block_selection_raises() -> None:
    try:
        resolve_pack_ids(option_keys=["life.office"], skip=False)
    except ValueError as exc:
        assert "at least one option" in str(exc)
    else:
        raise AssertionError("expected ValueError")
