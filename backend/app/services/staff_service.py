"""Staff console: user lookup, official pack authoring, and staff flag management."""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.i18n import DEFAULT_LOCALE, resolve_label
from app.core.marketplace import ESSENTIALS_PACK_SLUG, PackStatus
from app.models.icon_pack import IconPack
from app.models.user import User
from app.models.user_wallet import UserWallet
from app.services.marketplace_service import (
    MarketplaceError,
    _normalize_pack_labels,
    _slugify,
    _unique_pack_slug,
    get_pack_or_raise,
)


def search_users(db: Session, *, q: str | None, limit: int = 20) -> list[tuple[User, int]]:
    """Find users by email substring, exact id, or Telegram user id; newest first."""
    query = select(User, UserWallet.balance).outerjoin(UserWallet, UserWallet.user_id == User.id)
    term = (q or "").strip()
    if term:
        conditions: list[Any] = [User.email.ilike(f"%{term}%")]
        with contextlib.suppress(ValueError):
            conditions.append(User.id == uuid.UUID(term))
        if term.isdigit():
            conditions.append(User.telegram_user_id == int(term))
        query = query.where(or_(*conditions))
    rows = db.execute(query.order_by(User.created_at.desc()).limit(limit)).all()
    return [(user, int(balance or 0)) for user, balance in rows]


def create_official_pack(
    db: Session,
    *,
    staff: User,
    labels: dict[str, Any],
    slug: str | None = None,
    price_tokens: int = 0,
    sort_order: int = 0,
) -> IconPack:
    normalized = _normalize_pack_labels(labels)
    base = _slugify(slug or resolve_label(normalized["name"], DEFAULT_LOCALE))
    if base == ESSENTIALS_PACK_SLUG:
        base = f"{base}-2"
    pack = IconPack(
        slug=_unique_pack_slug(db, base=base),
        author_id=staff.id,
        is_official=True,
        status=PackStatus.DRAFT.value,
        price_tokens=price_tokens,
        labels=normalized,
        sort_order=sort_order,
    )
    db.add(pack)
    db.flush()
    return pack


def set_pack_sort_order(db: Session, *, pack_id: uuid.UUID, sort_order: int) -> IconPack:
    pack = get_pack_or_raise(db, pack_id)
    pack.sort_order = sort_order
    db.flush()
    return pack


def archive_pack(db: Session, *, staff: User, pack_id: uuid.UUID) -> IconPack:
    pack = get_pack_or_raise(db, pack_id)
    if pack.slug == ESSENTIALS_PACK_SLUG:
        raise MarketplaceError(
            "The essentials pack cannot be archived",
            code=ErrorCode.ICON_PACK_INVALID_STATUS,
            params={"status": pack.status},
        )
    pack.status = PackStatus.ARCHIVED.value
    pack.reviewed_at = datetime.now(UTC)
    pack.reviewed_by = staff.id
    db.flush()
    return pack


def set_user_staff(db: Session, *, user: User, is_staff: bool) -> User:
    user.is_staff = is_staff
    db.flush()
    return user
