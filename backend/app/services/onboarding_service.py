"""Onboarding completion: apply selected content packs and mark user done."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.i18n import resolve_label
from app.core.onboarding_packs import (
    AdditiveSuggestions,
    ComposedDefaults,
    compose_additive_suggestions,
    filter_suggestions,
    load_onboarding_catalog,
)
from app.models.user import User
from app.services.notification_settings_service import enable_daily_email_reminder
from app.services.user_provisioning import provision_composed_defaults


class OnboardingError(AppError):
    pass


def _local_today(timezone_name: str) -> date:
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except ZoneInfoNotFoundError:
        return datetime.now(UTC).date()


def get_onboarding_catalog_payload(*, locale: str) -> dict[str, Any]:
    catalog = load_onboarding_catalog()
    return {
        "questions": [
            {
                "block_id": question.block_id,
                "title": resolve_label(question.title, locale),
                "selection": question.selection,
                "max_selections": question.max_selections,
                "options": [
                    {
                        "key": option.key,
                        "label": resolve_label(option.label, locale),
                    }
                    for option in question.options
                ],
            }
            for question in catalog.questions
        ]
    }


def _suggestions_payload(suggestions: AdditiveSuggestions, *, locale: str) -> dict[str, Any]:
    return {
        "tag_groups": [
            {
                "slug": group.slug,
                "label": resolve_label(group.labels, locale),
                "pack_id": group.pack_id,
                "tags": [
                    {
                        "slug": tag.slug,
                        "label": resolve_label(tag.labels, locale),
                        "color": tag.color,
                        "icon": tag.icon,
                    }
                    for tag in group.tags
                ],
            }
            for group in suggestions.tag_groups
        ],
        "note_templates": [
            {
                "slug": template.slug,
                "label": resolve_label(template.labels, locale),
                "pack_id": template.pack_id,
                "body": resolve_label(template.bodies, locale),
            }
            for template in suggestions.note_templates
        ],
    }


def get_onboarding_suggestions_payload(*, option_keys: list[str], locale: str) -> dict[str, Any]:
    try:
        suggestions = compose_additive_suggestions(option_keys=option_keys)
    except ValueError as exc:
        raise OnboardingError(
            str(exc), code=ErrorCode.INVALID_ONBOARDING_OPTIONS, status_code=400
        ) from exc
    return _suggestions_payload(suggestions, locale=locale)


def _to_composed_without_goals(suggestions: AdditiveSuggestions) -> ComposedDefaults:
    return ComposedDefaults(
        pack_ids=suggestions.pack_ids,
        tag_groups=suggestions.tag_groups,
        note_templates=suggestions.note_templates,
        goals=(),
    )


def complete_onboarding(
    db: Session,
    user: User,
    *,
    skip: bool,
    option_keys: list[str] | None,
    tag_group_slugs: list[str] | None = None,
    note_template_slugs: list[str] | None = None,
    email_reminders: bool = False,
) -> User:
    if user.onboarding_completed_at is not None:
        raise OnboardingError(
            "Onboarding already completed",
            code=ErrorCode.ONBOARDING_ALREADY_COMPLETED,
            status_code=409,
        )

    if not skip:
        keys = list(option_keys or [])
        selected_groups = list(tag_group_slugs or [])
        selected_templates = list(note_template_slugs or [])
        try:
            available = compose_additive_suggestions(option_keys=keys)
            chosen = filter_suggestions(
                available,
                tag_group_slugs=selected_groups,
                note_template_slugs=selected_templates,
            )
        except ValueError as exc:
            raise OnboardingError(
                str(exc), code=ErrorCode.INVALID_ONBOARDING_OPTIONS, status_code=400
            ) from exc

        if chosen.tag_groups or chosen.note_templates:
            provision_composed_defaults(
                db,
                user.id,
                _to_composed_without_goals(chosen),
                starts_on=_local_today(user.timezone),
                include_goals=False,
                update_existing_visibility=False,
            )

    if email_reminders:
        enable_daily_email_reminder(db, user=user)

    user.onboarding_completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user
