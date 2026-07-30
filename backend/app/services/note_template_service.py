from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.i18n import DEFAULT_LOCALE, resolve_label
from app.models.note_template import NoteTemplate

_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")


class NoteTemplateError(AppError):
    pass


def list_note_templates(db: Session, *, user_id: uuid.UUID) -> list[NoteTemplate]:
    return list(
        db.scalars(
            select(NoteTemplate)
            .where(NoteTemplate.user_id == user_id)
            .order_by(NoteTemplate.sort_order, NoteTemplate.slug)
        ).all()
    )


def get_note_template(
    db: Session,
    *,
    user_id: uuid.UUID,
    template_id: uuid.UUID,
) -> NoteTemplate:
    template = db.scalar(
        select(NoteTemplate).where(
            NoteTemplate.id == template_id,
            NoteTemplate.user_id == user_id,
        )
    )
    if template is None:
        raise NoteTemplateError(
            "Note template not found", code=ErrorCode.NOTE_TEMPLATE_NOT_FOUND, status_code=404
        )
    return template


def create_note_template(
    db: Session,
    *,
    user_id: uuid.UUID,
    labels: dict[str, str],
    bodies: dict[str, str],
    slug: str | None = None,
    sort_order: int | None = None,
) -> NoteTemplate:
    resolved_slug = slug or _unique_template_slug(db, user_id=user_id, base=_slugify(labels))
    resolved_order = (
        sort_order
        if sort_order is not None
        else _next_sort_order(
            db,
            select(func.max(NoteTemplate.sort_order)).where(NoteTemplate.user_id == user_id),
        )
    )
    template = NoteTemplate(
        user_id=user_id,
        slug=resolved_slug,
        labels=labels,
        bodies=bodies,
        sort_order=resolved_order,
    )
    db.add(template)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise NoteTemplateError(
            "Note template slug already exists",
            code=ErrorCode.NOTE_TEMPLATE_SLUG_EXISTS,
            status_code=409,
        ) from exc
    return get_note_template(db, user_id=user_id, template_id=template.id)


def patch_note_template(
    db: Session,
    *,
    user_id: uuid.UUID,
    template_id: uuid.UUID,
    slug: str | None = None,
    labels: dict[str, str] | None = None,
    bodies: dict[str, str] | None = None,
    sort_order: int | None = None,
) -> NoteTemplate:
    template = get_note_template(db, user_id=user_id, template_id=template_id)
    if slug is not None:
        template.slug = slug
    if labels is not None:
        template.labels = labels
    if bodies is not None:
        template.bodies = bodies
    if sort_order is not None:
        template.sort_order = sort_order
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise NoteTemplateError(
            "Note template slug already exists",
            code=ErrorCode.NOTE_TEMPLATE_SLUG_EXISTS,
            status_code=409,
        ) from exc
    return get_note_template(db, user_id=user_id, template_id=template_id)


def delete_note_template(db: Session, *, user_id: uuid.UUID, template_id: uuid.UUID) -> None:
    template = get_note_template(db, user_id=user_id, template_id=template_id)
    db.delete(template)
    db.commit()


def reorder_note_templates(
    db: Session,
    *,
    user_id: uuid.UUID,
    ordered_ids: list[uuid.UUID],
) -> list[NoteTemplate]:
    templates = list_note_templates(db, user_id=user_id)
    by_id = {template.id: template for template in templates}
    if set(ordered_ids) != set(by_id):
        raise NoteTemplateError(
            "ordered_ids must include every note template exactly once",
            code=ErrorCode.NOTE_TEMPLATE_REORDER_MISMATCH,
            status_code=400,
        )
    for index, template_id in enumerate(ordered_ids):
        by_id[template_id].sort_order = index
    db.commit()
    return list_note_templates(db, user_id=user_id)


def serialize_note_template(template: NoteTemplate, *, locale: str) -> dict[str, Any]:
    return {
        "id": template.id,
        "slug": template.slug,
        "label": resolve_label(template.labels, locale),
        "labels": template.labels,
        "body": resolve_label(template.bodies, locale),
        "bodies": template.bodies,
        "sort_order": template.sort_order,
    }


def serialize_note_templates(
    templates: list[NoteTemplate],
    *,
    locale: str,
) -> list[dict[str, Any]]:
    return [serialize_note_template(template, locale=locale) for template in templates]


def _next_sort_order(db: Session, query: Select[Any]) -> int:
    current = db.scalar(query)
    return 0 if current is None else int(current) + 1


def _slugify(labels: dict[str, str]) -> str:
    raw = labels.get(DEFAULT_LOCALE) or next(iter(labels.values()))
    slug = _SLUGIFY_RE.sub("_", raw.lower()).strip("_")
    if not slug:
        slug = "item"
    if not slug[0].isalpha():
        slug = f"t_{slug}"
    return slug[:64]


def _unique_template_slug(db: Session, *, user_id: uuid.UUID, base: str) -> str:
    return _unique_slug(
        base,
        exists=lambda candidate: (
            db.scalar(
                select(NoteTemplate.id).where(
                    NoteTemplate.user_id == user_id,
                    NoteTemplate.slug == candidate,
                )
            )
            is not None
        ),
    )


def _unique_slug(base: str, *, exists: Callable[[str], bool]) -> str:
    candidate = base
    index = 2
    while exists(candidate):
        suffix = f"_{index}"
        candidate = f"{base[: 64 - len(suffix)]}{suffix}"
        index += 1
    return candidate
