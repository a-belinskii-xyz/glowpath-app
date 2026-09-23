"""Default tag groups copied to each user on registration (BASE pack)."""

from dataclasses import dataclass

from app.core.i18n import LocaleLabels
from app.core.onboarding_packs import get_base_pack

DEFAULT_TAG_COLOR = "#94a3b8"
DEFAULT_TAG_ICON_TYPE = "emoji"
DEFAULT_TAG_ICON = "🏷"


@dataclass(frozen=True, slots=True)
class DefaultTag:
    slug: str
    labels: LocaleLabels
    color: str = DEFAULT_TAG_COLOR
    icon: str = DEFAULT_TAG_ICON


@dataclass(frozen=True, slots=True)
class DefaultTagGroup:
    slug: str
    labels: LocaleLabels
    tags: tuple[DefaultTag, ...]


def _load_default_tag_groups() -> tuple[DefaultTagGroup, ...]:
    base = get_base_pack()
    return tuple(
        DefaultTagGroup(
            slug=group.slug,
            labels=dict(group.labels),
            tags=tuple(
                DefaultTag(
                    slug=tag.slug,
                    labels=dict(tag.labels),
                    color=tag.color,
                    icon=tag.icon,
                )
                for tag in group.tags
            ),
        )
        for group in sorted(base.tag_groups, key=lambda item: (item.sort_order, item.slug))
    )


DEFAULT_TAG_GROUPS: tuple[DefaultTagGroup, ...] = _load_default_tag_groups()

# Known seed / persona slugs → style (used by migration backfill).
KNOWN_TAG_STYLES: dict[str, tuple[str, str]] = {
    tag.slug: (tag.color, tag.icon) for group in DEFAULT_TAG_GROUPS for tag in group.tags
}
KNOWN_TAG_STYLES.update(
    {
        "running": ("#34d399", "🏃"),
        "reading": ("#60a5fa", "📖"),
        "cooking": ("#f59e0b", "🍳"),
        "family": ("#f472b6", "👨‍👩‍👧"),
        "friends": ("#60a5fa", "👥"),
        "colleagues": ("#94a3b8", "🧑‍💼"),
        "home": ("#f59e0b", "🏠"),
        "office": ("#60a5fa", "🏢"),
        "cafe": ("#d97706", "☕"),
        "outdoors": ("#34d399", "🌳"),
    }
)
