"""Visitor experiment: bootstrap, heartbeat, and staff analytics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.feature_flags import FeatureFlag, is_feature_enabled_for_visitor, targeting_for
from app.core.visitor_fingerprint import (
    canonical_fingerprint_payload,
    fingerprint_hash_from_payload,
)
from app.models.guest_device import GuestAuthEvent, GuestDevice
from app.models.visitor import Visitor, VisitorCohort

VISITOR_COOKIE_NAME = settings.guest_visitor_cookie_name


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    visitor_id: uuid.UUID
    guest_local_diary: bool
    cohort: str


@dataclass(frozen=True, slots=True)
class GuestExperimentSummary:
    control_visitors: int
    treatment_visitors: int
    treatment_active_7d: int
    control_converted: int
    treatment_converted: int
    treatment_median_entry_count_on_convert: float | None
    treatment_existing_login_skipped: int


def _cookie_max_age_seconds() -> int:
    return settings.guest_visitor_cookie_max_age_days * 24 * 60 * 60


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _as_float(value: object, default: float = 1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return default
    try:
        return float(value)
    except ValueError:
        return default


class VisitorCookieSettings(TypedDict):
    key: str
    httponly: bool
    samesite: Literal["lax", "strict", "none"]
    secure: bool
    max_age: int
    path: str


def visitor_cookie_settings() -> VisitorCookieSettings:
    return {
        "key": VISITOR_COOKIE_NAME,
        "httponly": True,
        "samesite": "lax",
        "secure": not settings.debug,
        "max_age": _cookie_max_age_seconds(),
        "path": "/",
    }


def _assign_cohort(visitor_id: uuid.UUID) -> str:
    if is_feature_enabled_for_visitor(FeatureFlag.GUEST_LOCAL_DIARY, visitor_id):
        return VisitorCohort.TREATMENT.value
    return VisitorCohort.CONTROL.value


def _guest_local_diary_enabled(cohort: str) -> bool:
    rule = targeting_for(FeatureFlag.GUEST_LOCAL_DIARY)
    if not rule.enabled:
        return False
    return cohort == VisitorCohort.TREATMENT.value


def _touch_visitor(visitor: Visitor, *, now: datetime) -> None:
    visitor.last_seen_at = now


def resolve_or_create_visitor(
    db: Session,
    *,
    cookie_visitor_id: uuid.UUID | None,
    fingerprint_payload: dict[str, object] | None,
    user_agent: str,
    accept_language: str,
) -> tuple[Visitor, bool]:
    now = datetime.now(UTC)
    created = False

    if cookie_visitor_id is not None:
        visitor = db.get(Visitor, cookie_visitor_id)
        if visitor is not None:
            _touch_visitor(visitor, now=now)
            return visitor, created

    fingerprint_hash: str | None = None
    if fingerprint_payload is not None:
        canonical = canonical_fingerprint_payload(
            user_agent=user_agent,
            accept_language=accept_language,
            timezone=str(fingerprint_payload.get("timezone", "")),
            screen_width=_as_int(fingerprint_payload.get("screen_width", 0)),
            screen_height=_as_int(fingerprint_payload.get("screen_height", 0)),
            screen_dpr=_as_float(fingerprint_payload.get("screen_dpr", 1)),
            platform=str(fingerprint_payload.get("platform", "")),
            max_touch_points=_as_int(fingerprint_payload.get("max_touch_points", 0)),
        )
        fingerprint_hash = fingerprint_hash_from_payload(canonical)
        visitor = db.scalar(select(Visitor).where(Visitor.fingerprint_hash == fingerprint_hash))
        if visitor is not None:
            _touch_visitor(visitor, now=now)
            return visitor, created

    visitor_id = uuid.uuid4()
    cohort = _assign_cohort(visitor_id)
    visitor = Visitor(
        id=visitor_id,
        fingerprint_hash=fingerprint_hash,
        cohort=cohort,
        last_seen_at=now,
    )
    db.add(visitor)
    db.flush()
    created = True
    return visitor, created


def bootstrap_visitor(
    db: Session,
    *,
    cookie_visitor_id: uuid.UUID | None,
    fingerprint_payload: dict[str, object] | None,
    user_agent: str,
    accept_language: str,
) -> BootstrapResult:
    visitor, _created = resolve_or_create_visitor(
        db,
        cookie_visitor_id=cookie_visitor_id,
        fingerprint_payload=fingerprint_payload,
        user_agent=user_agent,
        accept_language=accept_language,
    )
    db.commit()
    db.refresh(visitor)
    return BootstrapResult(
        visitor_id=visitor.id,
        guest_local_diary=_guest_local_diary_enabled(visitor.cohort),
        cohort=visitor.cohort,
    )


def _ensure_guest_device(db: Session, visitor: Visitor) -> GuestDevice:
    device = db.get(GuestDevice, visitor.id)
    if device is None:
        device = GuestDevice(id=visitor.id, last_seen_at=datetime.now(UTC))
        db.add(device)
        db.flush()
    return device


def record_guest_heartbeat(
    db: Session,
    *,
    visitor_id: uuid.UUID,
    timezone: str | None,
    locale: str | None,
    entry_count: int,
    onboarding_completed: bool,
) -> None:
    visitor = db.get(Visitor, visitor_id)
    if visitor is None:
        raise ValueError("visitor_not_found")
    if visitor.cohort != VisitorCohort.TREATMENT.value:
        raise ValueError("not_in_treatment")
    if not _guest_local_diary_enabled(visitor.cohort):
        raise ValueError("feature_disabled")

    now = datetime.now(UTC)
    _touch_visitor(visitor, now=now)
    device = _ensure_guest_device(db, visitor)
    device.last_seen_at = now
    if timezone:
        device.timezone = timezone
    if locale:
        device.locale = locale
    device.entry_count = max(0, entry_count)
    device.onboarding_completed = onboarding_completed
    db.commit()


def mark_visitor_converted(
    db: Session,
    *,
    visitor_id: uuid.UUID,
    user_id: uuid.UUID,
    auth_event: GuestAuthEvent,
) -> None:
    now = datetime.now(UTC)
    visitor = db.get(Visitor, visitor_id)
    if visitor is not None:
        visitor.converted_user_id = user_id
        visitor.converted_at = now
    device = db.get(GuestDevice, visitor_id)
    if device is not None:
        device.converted_user_id = user_id
        device.converted_at = now
        device.last_auth_event = auth_event.value


def get_experiment_summary(db: Session) -> GuestExperimentSummary:
    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)

    control_visitors = (
        db.scalar(
            select(func.count())
            .select_from(Visitor)
            .where(Visitor.cohort == VisitorCohort.CONTROL.value)
        )
        or 0
    )
    treatment_visitors = (
        db.scalar(
            select(func.count())
            .select_from(Visitor)
            .where(Visitor.cohort == VisitorCohort.TREATMENT.value)
        )
        or 0
    )
    treatment_active_7d = (
        db.scalar(
            select(func.count())
            .select_from(GuestDevice)
            .where(GuestDevice.last_seen_at >= week_ago)
        )
        or 0
    )
    control_converted = (
        db.scalar(
            select(func.count())
            .select_from(Visitor)
            .where(
                Visitor.cohort == VisitorCohort.CONTROL.value,
                Visitor.converted_user_id.is_not(None),
            )
        )
        or 0
    )
    treatment_converted = (
        db.scalar(
            select(func.count())
            .select_from(GuestDevice)
            .where(GuestDevice.converted_user_id.is_not(None))
        )
        or 0
    )
    treatment_existing_login_skipped = (
        db.scalar(
            select(func.count())
            .select_from(GuestDevice)
            .where(GuestDevice.last_auth_event == GuestAuthEvent.EXISTING_LOGIN_SKIPPED.value)
        )
        or 0
    )

    median_entry_count = db.scalar(
        select(func.percentile_cont(0.5).within_group(GuestDevice.entry_count)).where(
            GuestDevice.converted_user_id.is_not(None)
        )
    )

    return GuestExperimentSummary(
        control_visitors=control_visitors,
        treatment_visitors=treatment_visitors,
        treatment_active_7d=treatment_active_7d,
        control_converted=control_converted,
        treatment_converted=treatment_converted,
        treatment_median_entry_count_on_convert=(
            float(median_entry_count) if median_entry_count is not None else None
        ),
        treatment_existing_login_skipped=treatment_existing_login_skipped,
    )
