"""Onboarding content packs: load, resolve, and compose defaults for a user."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from app.core.i18n import LocaleLabels

PackKind = Literal["base", "life", "interest", "focus"]
BASE_PACK_ID = "base.default"
_PACKS_PATH = Path(__file__).resolve().parent / "data" / "onboarding_packs.json"


@dataclass(frozen=True, slots=True)
class PackTag:
    slug: str
    labels: LocaleLabels
    color: str
    icon_type: str
    icon: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class PackTagGroup:
    slug: str
    labels: LocaleLabels
    show_on_entry: bool
    sort_order: int
    tags: tuple[PackTag, ...]
    pack_id: str
    pack_priority: int


@dataclass(frozen=True, slots=True)
class PackNoteTemplate:
    slug: str
    labels: LocaleLabels
    bodies: LocaleLabels
    sort_order: int
    pack_id: str
    pack_priority: int


@dataclass(frozen=True, slots=True)
class PackGoal:
    slug: str
    labels: LocaleLabels
    times_per_week: int
    color: str
    icon_type: str
    icon: str
    show_on_entry: bool
    show_in_stats: bool
    sort_order: int
    pack_id: str
    pack_priority: int


@dataclass(frozen=True, slots=True)
class ContentPack:
    pack_id: str
    kind: PackKind
    title: LocaleLabels
    description: LocaleLabels
    onboarding_triggers: tuple[str, ...]
    priority: int
    tag_groups: tuple[PackTagGroup, ...]
    note_templates: tuple[PackNoteTemplate, ...]
    goals: tuple[PackGoal, ...]


@dataclass(frozen=True, slots=True)
class OnboardingOption:
    key: str
    label: LocaleLabels
    packs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OnboardingQuestion:
    block_id: str
    title: LocaleLabels
    selection: str
    max_selections: int
    options: tuple[OnboardingOption, ...]


@dataclass(frozen=True, slots=True)
class CompositionRules:
    on_skip: tuple[str, ...]
    max_show_on_entry_tag_groups: int
    always_show_on_entry_group_slugs: tuple[str, ...]
    dedupe: str


@dataclass(frozen=True, slots=True)
class ComposedDefaults:
    pack_ids: tuple[str, ...]
    tag_groups: tuple[PackTagGroup, ...]
    note_templates: tuple[PackNoteTemplate, ...]
    goals: tuple[PackGoal, ...]


@dataclass(frozen=True, slots=True)
class OnboardingCatalog:
    questions: tuple[OnboardingQuestion, ...]
    packs: dict[str, ContentPack]
    rules: CompositionRules
    option_keys: frozenset[str]


def _labels(raw: dict[str, Any]) -> LocaleLabels:
    return {str(key): str(value) for key, value in raw.items()}


def _parse_tag(raw: dict[str, Any]) -> PackTag:
    return PackTag(
        slug=str(raw["slug"]),
        labels=_labels(raw["labels"]),
        color=str(raw["color"]),
        icon_type=str(raw.get("icon_type") or "emoji"),
        icon=str(raw["icon"]),
        sort_order=int(raw.get("sort_order") or 0),
    )


def _parse_pack(raw: dict[str, Any]) -> ContentPack:
    pack_id = str(raw["pack_id"])
    priority = int(raw["priority"])
    tag_groups: list[PackTagGroup] = []
    for group_raw in raw.get("tag_groups") or []:
        tags = tuple(_parse_tag(tag) for tag in group_raw.get("tags") or [])
        tag_groups.append(
            PackTagGroup(
                slug=str(group_raw["slug"]),
                labels=_labels(group_raw["labels"]),
                show_on_entry=bool(group_raw.get("show_on_entry", False)),
                sort_order=int(group_raw.get("sort_order") or 0),
                tags=tags,
                pack_id=pack_id,
                pack_priority=priority,
            )
        )
    note_templates = tuple(
        PackNoteTemplate(
            slug=str(item["slug"]),
            labels=_labels(item["labels"]),
            bodies=_labels(item["bodies"]),
            sort_order=int(item.get("sort_order") or 0),
            pack_id=pack_id,
            pack_priority=priority,
        )
        for item in raw.get("note_templates") or []
    )
    goals = tuple(
        PackGoal(
            slug=str(item["slug"]),
            labels=_labels(item["labels"]),
            times_per_week=int(item["times_per_week"]),
            color=str(item.get("color") or "#60a5fa"),
            icon_type=str(item.get("icon_type") or "emoji"),
            icon=str(item.get("icon") or "🎯"),
            show_on_entry=bool(item.get("show_on_entry", False)),
            show_in_stats=bool(item.get("show_in_stats", False)),
            sort_order=int(item.get("sort_order") or 0),
            pack_id=pack_id,
            pack_priority=priority,
        )
        for item in raw.get("goals") or []
    )
    return ContentPack(
        pack_id=pack_id,
        kind=raw["kind"],
        title=_labels(raw["title"]),
        description=_labels(raw["description"]),
        onboarding_triggers=tuple(str(item) for item in raw.get("onboarding_triggers") or []),
        priority=priority,
        tag_groups=tuple(tag_groups),
        note_templates=note_templates,
        goals=goals,
    )


@lru_cache(maxsize=1)
def load_onboarding_catalog() -> OnboardingCatalog:
    raw = json.loads(_PACKS_PATH.read_text(encoding="utf-8"))
    packs = {pack.pack_id: pack for pack in (_parse_pack(item) for item in raw["packs"])}
    if BASE_PACK_ID not in packs:
        raise RuntimeError(f"Missing required pack {BASE_PACK_ID!r} in onboarding catalog")

    questions: list[OnboardingQuestion] = []
    option_keys: set[str] = set()
    for block in raw["onboarding_questions"]:
        options: list[OnboardingOption] = []
        for option_raw in block["options"]:
            option = OnboardingOption(
                key=str(option_raw["key"]),
                label=_labels(option_raw["label"]),
                packs=tuple(str(item) for item in option_raw["packs"]),
            )
            options.append(option)
            option_keys.add(option.key)
            for pack_id in option.packs:
                if pack_id not in packs:
                    raise RuntimeError(f"Unknown pack {pack_id!r} referenced by {option.key!r}")
        questions.append(
            OnboardingQuestion(
                block_id=str(block["block_id"]),
                title=_labels(block["title"]),
                selection=str(block["selection"]),
                max_selections=int(block["max_selections"]),
                options=tuple(options),
            )
        )

    rules_raw = raw["composition_rules"]
    rules = CompositionRules(
        on_skip=tuple(str(item) for item in rules_raw["on_skip"]),
        max_show_on_entry_tag_groups=int(rules_raw["max_show_on_entry_tag_groups"]),
        always_show_on_entry_group_slugs=tuple(
            str(item) for item in rules_raw["always_show_on_entry_group_slugs"]
        ),
        dedupe=str(rules_raw["dedupe"]),
    )
    return OnboardingCatalog(
        questions=tuple(questions),
        packs=packs,
        rules=rules,
        option_keys=frozenset(option_keys),
    )


def get_base_pack() -> ContentPack:
    return load_onboarding_catalog().packs[BASE_PACK_ID]


def resolve_pack_ids(*, option_keys: list[str] | None, skip: bool) -> tuple[str, ...]:
    catalog = load_onboarding_catalog()
    if skip:
        return catalog.rules.on_skip

    selected = list(option_keys or [])
    if not selected:
        raise ValueError("Select at least one onboarding option")

    unknown = sorted(set(selected) - catalog.option_keys)
    if unknown:
        raise ValueError(f"Unknown onboarding options: {', '.join(unknown)}")

    counts: dict[str, int] = {}
    for key in selected:
        block_id = key.split(".", 1)[0]
        counts[block_id] = counts.get(block_id, 0) + 1

    for question in catalog.questions:
        selected_in_block = counts.get(question.block_id, 0)
        if selected_in_block < 1:
            raise ValueError(f"Select at least one option in block {question.block_id!r}")
        if selected_in_block > question.max_selections:
            raise ValueError(
                f"Too many selections for block {question.block_id!r} "
                f"(max {question.max_selections})"
            )

    pack_ids: set[str] = {BASE_PACK_ID}
    for key in selected:
        for question in catalog.questions:
            for option in question.options:
                if option.key == key:
                    pack_ids.update(option.packs)

    return tuple(sorted(pack_ids, key=lambda pack_id: (-catalog.packs[pack_id].priority, pack_id)))


def _prefer(existing_priority: int, candidate_priority: int) -> bool:
    """Return True if candidate should replace existing (higher priority wins)."""
    return candidate_priority > existing_priority


def compose_packs(pack_ids: tuple[str, ...]) -> ComposedDefaults:
    catalog = load_onboarding_catalog()
    ordered_ids = tuple(
        sorted(
            set(pack_ids) | {BASE_PACK_ID},
            key=lambda pack_id: (-catalog.packs[pack_id].priority, pack_id),
        )
    )

    groups_by_slug: dict[str, PackTagGroup] = {}
    templates_by_slug: dict[str, PackNoteTemplate] = {}
    goals_by_slug: dict[str, PackGoal] = {}

    for pack_id in ordered_ids:
        pack = catalog.packs[pack_id]
        for group in pack.tag_groups:
            current_group = groups_by_slug.get(group.slug)
            if current_group is None or _prefer(current_group.pack_priority, group.pack_priority):
                # Merge tags when replacing/keeping: prefer higher priority tags by slug.
                if current_group is None:
                    groups_by_slug[group.slug] = group
                else:
                    tags_by_slug = {tag.slug: tag for tag in current_group.tags}
                    for tag in group.tags:
                        tags_by_slug[tag.slug] = tag
                    merged_tags = tuple(
                        sorted(tags_by_slug.values(), key=lambda item: (item.sort_order, item.slug))
                    )
                    groups_by_slug[group.slug] = PackTagGroup(
                        slug=group.slug,
                        labels=group.labels,
                        show_on_entry=group.show_on_entry,
                        sort_order=group.sort_order,
                        tags=merged_tags,
                        pack_id=group.pack_id,
                        pack_priority=group.pack_priority,
                    )
            else:
                tags_by_slug = {tag.slug: tag for tag in current_group.tags}
                changed = False
                for tag in group.tags:
                    if tag.slug not in tags_by_slug:
                        tags_by_slug[tag.slug] = tag
                        changed = True
                if changed:
                    merged_tags = tuple(
                        sorted(tags_by_slug.values(), key=lambda item: (item.sort_order, item.slug))
                    )
                    groups_by_slug[group.slug] = PackTagGroup(
                        slug=current_group.slug,
                        labels=current_group.labels,
                        show_on_entry=current_group.show_on_entry,
                        sort_order=current_group.sort_order,
                        tags=merged_tags,
                        pack_id=current_group.pack_id,
                        pack_priority=current_group.pack_priority,
                    )

        for template in pack.note_templates:
            current_template = templates_by_slug.get(template.slug)
            if current_template is None or _prefer(
                current_template.pack_priority, template.pack_priority
            ):
                templates_by_slug[template.slug] = template

        for goal in pack.goals:
            current_goal = goals_by_slug.get(goal.slug)
            if current_goal is None or _prefer(current_goal.pack_priority, goal.pack_priority):
                goals_by_slug[goal.slug] = goal

    groups = _apply_show_on_entry(
        tuple(
            sorted(
                groups_by_slug.values(),
                key=lambda item: (-item.pack_priority, item.sort_order, item.slug),
            )
        ),
        catalog.rules,
    )
    templates = tuple(
        sorted(
            templates_by_slug.values(),
            key=lambda item: (-item.pack_priority, item.sort_order, item.slug),
        )
    )
    goals = tuple(
        sorted(
            goals_by_slug.values(),
            key=lambda item: (-item.pack_priority, item.sort_order, item.slug),
        )
    )
    return ComposedDefaults(
        pack_ids=ordered_ids,
        tag_groups=groups,
        note_templates=templates,
        goals=goals,
    )


def _apply_show_on_entry(
    groups: tuple[PackTagGroup, ...],
    rules: CompositionRules,
) -> tuple[PackTagGroup, ...]:
    always = set(rules.always_show_on_entry_group_slugs)
    limit = rules.max_show_on_entry_tag_groups

    always_groups = [group for group in groups if group.slug in always]
    pack_groups = sorted(
        [group for group in groups if group.slug not in always and group.pack_id != BASE_PACK_ID],
        key=lambda item: (-item.pack_priority, item.sort_order, item.slug),
    )
    base_rest = sorted(
        [group for group in groups if group.slug not in always and group.pack_id == BASE_PACK_ID],
        key=lambda item: (item.sort_order, item.slug),
    )

    visible_slugs = {group.slug for group in always_groups}
    for group in [*pack_groups, *base_rest]:
        if len(visible_slugs) >= limit:
            break
        visible_slugs.add(group.slug)

    return tuple(
        PackTagGroup(
            slug=group.slug,
            labels=group.labels,
            show_on_entry=group.slug in visible_slugs,
            sort_order=index,
            tags=group.tags,
            pack_id=group.pack_id,
            pack_priority=group.pack_priority,
        )
        for index, group in enumerate(groups)
    )


def compose_for_options(*, option_keys: list[str] | None, skip: bool) -> ComposedDefaults:
    return compose_packs(resolve_pack_ids(option_keys=option_keys, skip=skip))


@dataclass(frozen=True, slots=True)
class AdditiveSuggestions:
    """Tag groups and templates from non-BASE packs only (no goals)."""

    pack_ids: tuple[str, ...]
    tag_groups: tuple[PackTagGroup, ...]
    note_templates: tuple[PackNoteTemplate, ...]


def compose_additive_suggestions(*, option_keys: list[str]) -> AdditiveSuggestions:
    """Build opt-in suggestions for onboarding (excludes BASE content and all goals)."""
    pack_ids = resolve_pack_ids(option_keys=option_keys, skip=False)
    additive_ids = tuple(pack_id for pack_id in pack_ids if pack_id != BASE_PACK_ID)
    if not additive_ids:
        return AdditiveSuggestions(pack_ids=(), tag_groups=(), note_templates=())

    catalog = load_onboarding_catalog()
    groups_by_slug: dict[str, PackTagGroup] = {}
    templates_by_slug: dict[str, PackNoteTemplate] = {}

    for pack_id in additive_ids:
        pack = catalog.packs[pack_id]
        for group in pack.tag_groups:
            current_group = groups_by_slug.get(group.slug)
            if current_group is None or _prefer(current_group.pack_priority, group.pack_priority):
                groups_by_slug[group.slug] = group
            else:
                tags_by_slug = {tag.slug: tag for tag in current_group.tags}
                changed = False
                for tag in group.tags:
                    if tag.slug not in tags_by_slug:
                        tags_by_slug[tag.slug] = tag
                        changed = True
                if changed:
                    groups_by_slug[group.slug] = PackTagGroup(
                        slug=current_group.slug,
                        labels=current_group.labels,
                        show_on_entry=current_group.show_on_entry,
                        sort_order=current_group.sort_order,
                        tags=tuple(
                            sorted(
                                tags_by_slug.values(),
                                key=lambda item: (item.sort_order, item.slug),
                            )
                        ),
                        pack_id=current_group.pack_id,
                        pack_priority=current_group.pack_priority,
                    )

        for template in pack.note_templates:
            current_template = templates_by_slug.get(template.slug)
            if current_template is None or _prefer(
                current_template.pack_priority, template.pack_priority
            ):
                templates_by_slug[template.slug] = template

    return AdditiveSuggestions(
        pack_ids=additive_ids,
        tag_groups=tuple(
            sorted(
                groups_by_slug.values(),
                key=lambda item: (-item.pack_priority, item.sort_order, item.slug),
            )
        ),
        note_templates=tuple(
            sorted(
                templates_by_slug.values(),
                key=lambda item: (-item.pack_priority, item.sort_order, item.slug),
            )
        ),
    )


def filter_suggestions(
    suggestions: AdditiveSuggestions,
    *,
    tag_group_slugs: list[str],
    note_template_slugs: list[str],
) -> AdditiveSuggestions:
    allowed_groups = {group.slug for group in suggestions.tag_groups}
    allowed_templates = {template.slug for template in suggestions.note_templates}
    unknown_groups = sorted(set(tag_group_slugs) - allowed_groups)
    unknown_templates = sorted(set(note_template_slugs) - allowed_templates)
    if unknown_groups or unknown_templates:
        parts: list[str] = []
        if unknown_groups:
            parts.append(f"tag groups: {', '.join(unknown_groups)}")
        if unknown_templates:
            parts.append(f"templates: {', '.join(unknown_templates)}")
        raise ValueError(f"Unknown onboarding selections: {'; '.join(parts)}")

    selected_groups = set(tag_group_slugs)
    selected_templates = set(note_template_slugs)
    return AdditiveSuggestions(
        pack_ids=suggestions.pack_ids,
        tag_groups=tuple(
            group for group in suggestions.tag_groups if group.slug in selected_groups
        ),
        note_templates=tuple(
            template
            for template in suggestions.note_templates
            if template.slug in selected_templates
        ),
    )
