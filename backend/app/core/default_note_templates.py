"""Default note templates copied to each user on registration (BASE pack)."""

from dataclasses import dataclass

from app.core.i18n import LocaleLabels
from app.core.onboarding_packs import get_base_pack


@dataclass(frozen=True, slots=True)
class DefaultNoteTemplate:
    slug: str
    labels: LocaleLabels
    bodies: LocaleLabels


def _load_default_note_templates() -> tuple[DefaultNoteTemplate, ...]:
    base = get_base_pack()
    return tuple(
        DefaultNoteTemplate(
            slug=template.slug,
            labels=dict(template.labels),
            bodies=dict(template.bodies),
        )
        for template in sorted(base.note_templates, key=lambda item: (item.sort_order, item.slug))
    )


DEFAULT_NOTE_TEMPLATES: tuple[DefaultNoteTemplate, ...] = _load_default_note_templates()
