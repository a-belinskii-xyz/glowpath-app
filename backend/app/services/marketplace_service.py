"""Icon marketplace: packs, catalog icons, unlocks, studio, and staff moderation."""

from __future__ import annotations

import contextlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.i18n import DEFAULT_LOCALE, LocaleLabels, resolve_label
from app.core.marketplace import (
    ALLOWED_CATALOG_MIME_TYPES,
    ESSENTIALS_PACK_SLUG,
    MAX_CATALOG_ICON_BYTES,
    MAX_SEARCH_TAGS_PER_ICON,
    MAX_SUGGESTED_COLORS,
    MIN_SUGGESTED_COLORS,
    PackStatus,
    WalletLedgerKind,
)
from app.core.mood_scale import MoodScore, is_valid_hex_color
from app.models.catalog_icon import CatalogIcon
from app.models.catalog_icon_search_tag import CatalogIconSearchTag
from app.models.icon_pack import IconPack
from app.models.icon_pack_unlock import IconPackUnlock
from app.models.icon_search_tag import IconSearchTag
from app.models.user import User
from app.models.wallet_ledger import WalletLedger
from app.services.storage import ObjectStorage, StorageError
from app.services.wallet_service import WalletError, apply_ledger_delta, get_or_create_wallet

_UNSAFE_FILENAME_RE = re.compile(r"[^\w.\-]+", re.ASCII)
_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")


class MarketplaceError(AppError):
    pass


def _safe_filename(name: str) -> str:
    cleaned = _UNSAFE_FILENAME_RE.sub("_", name.strip()).strip("._")
    if not cleaned:
        return "file"
    return cleaned[:200]


def _slugify(raw: str) -> str:
    slug = _SLUGIFY_RE.sub("-", raw.lower()).strip("-")
    if not slug:
        slug = "item"
    if not slug[0].isalpha():
        slug = f"p-{slug}"
    return slug[:64]


def _unique_pack_slug(db: Session, *, base: str) -> str:
    candidate = base
    index = 2
    while db.scalar(select(IconPack.id).where(IconPack.slug == candidate)) is not None:
        suffix = f"-{index}"
        candidate = f"{base[: 64 - len(suffix)]}{suffix}"
        index += 1
    return candidate


def _unique_icon_slug(db: Session, *, pack_id: uuid.UUID, base: str) -> str:
    candidate = base
    index = 2
    while (
        db.scalar(
            select(CatalogIcon.id).where(
                CatalogIcon.pack_id == pack_id,
                CatalogIcon.slug == candidate,
            )
        )
        is not None
    ):
        suffix = f"-{index}"
        candidate = f"{base[: 64 - len(suffix)]}{suffix}"
        index += 1
    return candidate


def _normalize_locale_labels(raw: Any, *, code: ErrorCode, field: str) -> LocaleLabels:
    if not isinstance(raw, dict) or not raw:
        raise MarketplaceError(
            f"Invalid {field} labels",
            code=code,
            params={"field": field},
        )
    labels: LocaleLabels = {}
    for locale, value in raw.items():
        if not isinstance(locale, str) or not isinstance(value, str):
            raise MarketplaceError(
                f"Invalid {field} labels",
                code=code,
                params={"field": field},
            )
        cleaned = value.strip()
        if not cleaned:
            raise MarketplaceError(
                f"Invalid {field} labels",
                code=code,
                params={"field": field},
            )
        labels[locale.strip().lower()[:16]] = cleaned[:200]
    if DEFAULT_LOCALE not in labels and "en" not in labels:
        # allow ru-only if at least one label exists; resolve_label falls back
        pass
    return labels


def _normalize_pack_labels(raw: Any) -> dict[str, LocaleLabels]:
    if not isinstance(raw, dict):
        raise MarketplaceError("Invalid pack labels", code=ErrorCode.INVALID_PACK_LABELS)
    name = _normalize_locale_labels(
        raw.get("name"),
        code=ErrorCode.INVALID_PACK_LABELS,
        field="name",
    )
    description_raw = raw.get("description")
    if description_raw is None:
        description: LocaleLabels = {DEFAULT_LOCALE: ""}
    else:
        description = _normalize_locale_labels(
            description_raw,
            code=ErrorCode.INVALID_PACK_LABELS,
            field="description",
        )
    return {"name": name, "description": description}


def _normalize_suggested_colors(raw: Any) -> list[str]:
    if not isinstance(raw, list) or not (MIN_SUGGESTED_COLORS <= len(raw) <= MAX_SUGGESTED_COLORS):
        raise MarketplaceError(
            f"suggested_colors must have {MIN_SUGGESTED_COLORS}–{MAX_SUGGESTED_COLORS} hex colors",
            code=ErrorCode.INVALID_SUGGESTED_COLORS,
            params={
                "min": str(MIN_SUGGESTED_COLORS),
                "max": str(MAX_SUGGESTED_COLORS),
            },
        )
    colors: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not is_valid_hex_color(item):
            raise MarketplaceError(
                f"Invalid suggested color: {item!r}",
                code=ErrorCode.INVALID_SUGGESTED_COLORS,
                params={"color": str(item)},
            )
        colors.append(item.lower())
    return colors


def _normalize_suggested_mood_scores(raw: Any) -> list[int]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise MarketplaceError(
            "suggested_mood_scores must be a list of scores 1–5",
            code=ErrorCode.INVALID_SUGGESTED_MOOD_SCORES,
        )
    scores: list[int] = []
    seen: set[int] = set()
    for item in raw:
        try:
            score = MoodScore(int(item))
        except (TypeError, ValueError) as exc:
            raise MarketplaceError(
                f"Invalid suggested mood score: {item!r}",
                code=ErrorCode.INVALID_SUGGESTED_MOOD_SCORES,
                params={"score": str(item)},
            ) from exc
        if score.value not in seen:
            seen.add(score.value)
            scores.append(score.value)
    return scores


def _resolve_search_tags(db: Session, *, slugs: list[str] | None) -> list[IconSearchTag]:
    if not slugs:
        return []
    if len(slugs) > MAX_SEARCH_TAGS_PER_ICON:
        raise MarketplaceError(
            f"At most {MAX_SEARCH_TAGS_PER_ICON} search tags per icon",
            code=ErrorCode.SEARCH_TAG_LIMIT,
            params={"max": str(MAX_SEARCH_TAGS_PER_ICON)},
        )
    cleaned = []
    seen: set[str] = set()
    for slug in slugs:
        value = slug.strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    if not cleaned:
        return []
    tags = list(
        db.scalars(
            select(IconSearchTag).where(
                IconSearchTag.slug.in_(cleaned),
                IconSearchTag.is_active.is_(True),
            )
        ).all()
    )
    found = {tag.slug for tag in tags}
    missing = [slug for slug in cleaned if slug not in found]
    if missing:
        raise MarketplaceError(
            f"Unknown search tag: {missing[0]}",
            code=ErrorCode.SEARCH_TAG_NOT_FOUND,
            params={"slug": missing[0]},
            status_code=404,
        )
    by_slug = {tag.slug: tag for tag in tags}
    return [by_slug[slug] for slug in cleaned]


def _build_catalog_storage_key(
    *,
    pack_id: uuid.UUID,
    icon_id: uuid.UUID,
    original_name: str,
) -> str:
    return f"catalog/{pack_id}/{icon_id}_{_safe_filename(original_name)}"


def _validate_image_payload(*, data: bytes, content_type: str) -> str:
    mime_type = content_type.split(";")[0].strip().lower()
    if mime_type not in ALLOWED_CATALOG_MIME_TYPES:
        raise MarketplaceError(
            "Unsupported image MIME type",
            code=ErrorCode.UNSUPPORTED_IMAGE_MIME,
            params={"mime": mime_type},
        )
    if len(data) > MAX_CATALOG_ICON_BYTES:
        raise MarketplaceError(
            "Icon exceeds 512 KB limit",
            code=ErrorCode.ICON_TOO_LARGE,
            params={"limit": "512KB"},
        )
    return mime_type


def _pack_is_unlocked(db: Session, *, user_id: uuid.UUID, pack_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(IconPackUnlock.id).where(
                IconPackUnlock.user_id == user_id,
                IconPackUnlock.pack_id == pack_id,
            )
        )
        is not None
    )


def user_can_view_pack(user: User, pack: IconPack) -> bool:
    if pack.status == PackStatus.PUBLISHED.value:
        return True
    if user.is_staff:
        return True
    return pack.author_id is not None and pack.author_id == user.id


def user_can_assign_catalog_icon(
    db: Session,
    *,
    user: User,
    icon: CatalogIcon,
    pack: IconPack | None = None,
) -> bool:
    pack = pack or icon.pack
    if user.is_staff:
        return True
    if pack.author_id is not None and pack.author_id == user.id:
        return True
    if pack.status != PackStatus.PUBLISHED.value:
        return False
    if pack.price_tokens == 0:
        return True
    if _pack_is_unlocked(db, user_id=user.id, pack_id=pack.id):
        return True
    from app.models.user_catalog_icon_unlock import UserCatalogIconUnlock

    return (
        db.scalar(
            select(UserCatalogIconUnlock.id).where(
                UserCatalogIconUnlock.user_id == user.id,
                UserCatalogIconUnlock.catalog_icon_id == icon.id,
            )
        )
        is not None
    )


def can_assign_catalog_icon(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: str,
) -> bool:
    try:
        parsed = uuid.UUID(icon_id)
    except ValueError:
        return False
    icon = db.scalar(
        select(CatalogIcon).options(selectinload(CatalogIcon.pack)).where(CatalogIcon.id == parsed)
    )
    if icon is None:
        return False
    user = db.get(User, user_id)
    if user is None:
        return False
    return user_can_assign_catalog_icon(db, user=user, icon=icon)


def get_pack_or_raise(db: Session, pack_id: uuid.UUID) -> IconPack:
    pack = db.get(IconPack, pack_id)
    if pack is None:
        raise MarketplaceError(
            "Icon pack not found",
            code=ErrorCode.ICON_PACK_NOT_FOUND,
            status_code=404,
        )
    return pack


def get_pack_by_ref(db: Session, ref: str) -> IconPack:
    """Resolve a pack by UUID or slug."""
    raw = ref.strip()
    if not raw:
        raise MarketplaceError(
            "Icon pack not found",
            code=ErrorCode.ICON_PACK_NOT_FOUND,
            status_code=404,
        )
    try:
        pack_id = uuid.UUID(raw)
    except ValueError:
        pack = db.scalar(select(IconPack).where(IconPack.slug == raw.lower()))
    else:
        pack = db.get(IconPack, pack_id)
        if pack is None:
            pack = db.scalar(select(IconPack).where(IconPack.slug == raw.lower()))
    if pack is None:
        raise MarketplaceError(
            "Icon pack not found",
            code=ErrorCode.ICON_PACK_NOT_FOUND,
            status_code=404,
        )
    return pack


def get_catalog_icon_or_raise(db: Session, icon_id: uuid.UUID) -> CatalogIcon:
    icon = db.scalar(
        select(CatalogIcon)
        .options(
            selectinload(CatalogIcon.pack),
            selectinload(CatalogIcon.search_tags),
        )
        .where(CatalogIcon.id == icon_id)
    )
    if icon is None:
        raise MarketplaceError(
            "Catalog icon not found",
            code=ErrorCode.CATALOG_ICON_NOT_FOUND,
            status_code=404,
        )
    return icon


def list_search_tags(db: Session, *, active_only: bool = True) -> list[IconSearchTag]:
    query = select(IconSearchTag).order_by(IconSearchTag.sort_order, IconSearchTag.slug)
    if active_only:
        query = query.where(IconSearchTag.is_active.is_(True))
    return list(db.scalars(query).all())


def create_search_tag(
    db: Session,
    *,
    slug: str,
    labels: dict[str, str],
    sort_order: int = 0,
    is_active: bool = True,
) -> IconSearchTag:
    cleaned_slug = _slugify(slug)
    if db.scalar(select(IconSearchTag.id).where(IconSearchTag.slug == cleaned_slug)):
        raise MarketplaceError(
            "Search tag slug already exists",
            code=ErrorCode.SEARCH_TAG_SLUG_EXISTS,
            params={"slug": cleaned_slug},
        )
    tag = IconSearchTag(
        slug=cleaned_slug,
        labels=_normalize_locale_labels(
            labels,
            code=ErrorCode.INVALID_ICON_LABELS,
            field="labels",
        ),
        sort_order=sort_order,
        is_active=is_active,
    )
    db.add(tag)
    db.flush()
    return tag


def update_search_tag(
    db: Session,
    *,
    tag_id: uuid.UUID,
    labels: dict[str, str] | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
) -> IconSearchTag:
    tag = db.get(IconSearchTag, tag_id)
    if tag is None:
        raise MarketplaceError(
            "Search tag not found",
            code=ErrorCode.SEARCH_TAG_NOT_FOUND,
            status_code=404,
        )
    if labels is not None:
        tag.labels = _normalize_locale_labels(
            labels,
            code=ErrorCode.INVALID_ICON_LABELS,
            field="labels",
        )
    if sort_order is not None:
        tag.sort_order = sort_order
    if is_active is not None:
        tag.is_active = is_active
    db.flush()
    return tag


def delete_search_tag(db: Session, *, tag_id: uuid.UUID) -> None:
    tag = db.get(IconSearchTag, tag_id)
    if tag is None:
        raise MarketplaceError(
            "Search tag not found",
            code=ErrorCode.SEARCH_TAG_NOT_FOUND,
            status_code=404,
        )
    db.delete(tag)
    db.flush()


def list_published_packs(
    db: Session,
    *,
    user: User,
    q: str | None = None,
    tag: str | None = None,
    official: bool | None = None,
    unlocked: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[IconPack]:
    query = (
        select(IconPack)
        .where(IconPack.status == PackStatus.PUBLISHED.value)
        .order_by(IconPack.sort_order, IconPack.published_at.desc().nullslast())
    )
    if official is not None:
        query = query.where(IconPack.is_official.is_(official))
    if q:
        needle = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(IconPack.labels["name"]["en"].astext).like(needle),
                func.lower(IconPack.labels["name"]["ru"].astext).like(needle),
                func.lower(IconPack.slug).like(needle),
            )
        )
    if tag:
        query = (
            query.join(CatalogIcon, CatalogIcon.pack_id == IconPack.id)
            .join(CatalogIconSearchTag, CatalogIconSearchTag.icon_id == CatalogIcon.id)
            .join(IconSearchTag, IconSearchTag.id == CatalogIconSearchTag.tag_id)
            .where(IconSearchTag.slug == tag.strip().lower())
            .distinct()
        )
    if unlocked is True:
        query = query.join(
            IconPackUnlock,
            and_(
                IconPackUnlock.pack_id == IconPack.id,
                IconPackUnlock.user_id == user.id,
            ),
        )
    elif unlocked is False:
        unlocked_ids = select(IconPackUnlock.pack_id).where(IconPackUnlock.user_id == user.id)
        query = query.where(
            or_(
                IconPack.price_tokens == 0,
                IconPack.id.notin_(unlocked_ids),
            ),
            IconPack.price_tokens > 0,
        )
    return list(db.scalars(query.limit(limit).offset(offset)).unique().all())


def get_pack_detail(
    db: Session,
    *,
    user: User,
    pack_id: uuid.UUID,
) -> IconPack:
    pack = db.scalar(
        select(IconPack)
        .options(
            selectinload(IconPack.icons).selectinload(CatalogIcon.search_tags),
        )
        .where(IconPack.id == pack_id)
    )
    if pack is None or not user_can_view_pack(user, pack):
        raise MarketplaceError(
            "Icon pack not found",
            code=ErrorCode.ICON_PACK_NOT_FOUND,
            status_code=404,
        )
    return pack


def search_icons(
    db: Session,
    *,
    user: User,
    q: str | None = None,
    tags: list[str] | None = None,
    pack_id: uuid.UUID | None = None,
    suggested_mood: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[CatalogIcon]:
    query = (
        select(CatalogIcon)
        .join(IconPack, IconPack.id == CatalogIcon.pack_id)
        .options(
            selectinload(CatalogIcon.pack),
            selectinload(CatalogIcon.search_tags),
        )
        .order_by(CatalogIcon.sort_order, CatalogIcon.created_at.desc())
    )
    if not user.is_staff:
        query = query.where(
            or_(
                IconPack.status == PackStatus.PUBLISHED.value,
                IconPack.author_id == user.id,
            )
        )
    if pack_id is not None:
        query = query.where(CatalogIcon.pack_id == pack_id)
    if q:
        needle = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(CatalogIcon.labels["en"].astext).like(needle),
                func.lower(CatalogIcon.labels["ru"].astext).like(needle),
                func.lower(CatalogIcon.slug).like(needle),
            )
        )
    if suggested_mood is not None:
        try:
            MoodScore(suggested_mood)
        except ValueError as exc:
            raise MarketplaceError(
                f"Invalid suggested mood score: {suggested_mood}",
                code=ErrorCode.INVALID_SUGGESTED_MOOD_SCORES,
                params={"score": str(suggested_mood)},
            ) from exc
        query = query.where(CatalogIcon.suggested_mood_scores.contains([suggested_mood]))
    if tags:
        cleaned = [t.strip().lower() for t in tags if t.strip()]
        if cleaned:
            matching = (
                select(CatalogIconSearchTag.icon_id)
                .join(IconSearchTag, IconSearchTag.id == CatalogIconSearchTag.tag_id)
                .where(IconSearchTag.slug.in_(cleaned))
                .group_by(CatalogIconSearchTag.icon_id)
                .having(func.count(func.distinct(IconSearchTag.slug)) >= len(cleaned))
            )
            query = query.where(CatalogIcon.id.in_(matching))
    return list(db.scalars(query.limit(limit).offset(offset)).unique().all())


def unlock_pack(
    db: Session,
    *,
    user: User,
    pack_id: uuid.UUID,
) -> IconPackUnlock:
    pack = get_pack_or_raise(db, pack_id)
    if pack.status != PackStatus.PUBLISHED.value:
        raise MarketplaceError(
            "Icon pack is not published",
            code=ErrorCode.ICON_PACK_NOT_PUBLISHED,
            status_code=400,
        )
    existing = db.scalar(
        select(IconPackUnlock).where(
            IconPackUnlock.user_id == user.id,
            IconPackUnlock.pack_id == pack.id,
        )
    )
    if existing is not None:
        return existing
    if pack.price_tokens > 0:
        try:
            apply_ledger_delta(
                db,
                user_id=user.id,
                delta=-pack.price_tokens,
                kind=WalletLedgerKind.UNLOCK_PACK,
                pack_id=pack.id,
                note=f"Unlock pack {pack.slug}",
            )
        except WalletError as exc:
            raise MarketplaceError(
                exc.message,
                code=exc.code,
                status_code=exc.status_code,
                params=exc.params,
            ) from exc
    else:
        get_or_create_wallet(db, user_id=user.id)
    unlock = IconPackUnlock(user_id=user.id, pack_id=pack.id)
    db.add(unlock)
    db.flush()
    return unlock


def _latest_unlock_charge(
    db: Session,
    *,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
) -> WalletLedger | None:
    return db.scalar(
        select(WalletLedger)
        .where(
            WalletLedger.user_id == user_id,
            WalletLedger.pack_id == pack_id,
            WalletLedger.kind == WalletLedgerKind.UNLOCK_PACK.value,
            WalletLedger.delta < 0,
        )
        .order_by(WalletLedger.created_at.desc())
        .limit(1)
    )


def revoke_pack_unlock(
    db: Session,
    *,
    user: User,
    pack_id: uuid.UUID,
    note: str | None = None,
    created_by: uuid.UUID | None = None,
    refund_amount: int | None = None,
) -> tuple[IconPack, WalletLedger | None, int]:
    """Remove a pack unlock and credit a refund ledger row.

    ``refund_amount`` defaults to whatever the user originally paid for this
    pack (0 if it was free / never charged). Pass 0 to lock without refund.
    """
    pack = get_pack_or_raise(db, pack_id)
    unlock = db.scalar(
        select(IconPackUnlock).where(
            IconPackUnlock.user_id == user.id,
            IconPackUnlock.pack_id == pack.id,
        )
    )
    if unlock is None:
        raise MarketplaceError(
            "Icon pack is not unlocked for this user",
            code=ErrorCode.ICON_PACK_NOT_UNLOCKED,
            status_code=404,
        )
    if refund_amount is None:
        charge = _latest_unlock_charge(db, user_id=user.id, pack_id=pack.id)
        refund_amount = abs(charge.delta) if charge is not None else 0
    if refund_amount < 0:
        raise MarketplaceError(
            "Refund amount must be zero or positive",
            code=ErrorCode.WALLET_GRANT_INVALID,
        )
    db.delete(unlock)
    db.flush()
    entry: WalletLedger | None = None
    if refund_amount > 0:
        try:
            _wallet, entry = apply_ledger_delta(
                db,
                user_id=user.id,
                delta=refund_amount,
                kind=WalletLedgerKind.REFUND,
                pack_id=pack.id,
                note=note or f"Revoke pack {pack.slug}",
                created_by=created_by,
            )
        except WalletError as exc:
            raise MarketplaceError(
                exc.message,
                code=exc.code,
                status_code=exc.status_code,
                params=exc.params,
            ) from exc
    return pack, entry, refund_amount


def list_user_unlocks(db: Session, *, user_id: uuid.UUID) -> list[IconPackUnlock]:
    return list(
        db.scalars(
            select(IconPackUnlock)
            .options(selectinload(IconPackUnlock.pack))
            .where(IconPackUnlock.user_id == user_id)
            .order_by(IconPackUnlock.unlocked_at.desc())
        ).all()
    )


def download_catalog_icon(
    db: Session,
    *,
    user: User,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> tuple[CatalogIcon, bytes]:
    icon = get_catalog_icon_or_raise(db, icon_id)
    if not user_can_view_pack(user, icon.pack):
        raise MarketplaceError(
            "Catalog icon not found",
            code=ErrorCode.CATALOG_ICON_NOT_FOUND,
            status_code=404,
        )
    try:
        data = storage.get_object(key=icon.storage_key)
    except StorageError:
        raise
    return icon, data


# --- Studio (author) ---


def _assert_pack_editable(pack: IconPack, user: User) -> None:
    if user.is_staff and pack.is_official:
        return
    if pack.author_id != user.id:
        raise MarketplaceError(
            "Icon pack not found",
            code=ErrorCode.ICON_PACK_NOT_FOUND,
            status_code=404,
        )
    if pack.status not in {
        PackStatus.DRAFT.value,
        PackStatus.REJECTED.value,
    }:
        raise MarketplaceError(
            "Published or pending packs cannot be edited",
            code=ErrorCode.ICON_PACK_NOT_EDITABLE,
        )


def create_studio_pack(
    db: Session,
    *,
    user: User,
    labels: dict[str, Any],
    slug: str | None = None,
    price_tokens: int = 0,
) -> IconPack:
    if price_tokens < 0:
        raise MarketplaceError(
            "price_tokens must be >= 0",
            code=ErrorCode.INVALID_PACK_LABELS,
        )
    base = _slugify(slug or resolve_label(_normalize_pack_labels(labels)["name"], DEFAULT_LOCALE))
    pack = IconPack(
        slug=_unique_pack_slug(db, base=base),
        author_id=user.id,
        is_official=False,
        status=PackStatus.DRAFT.value,
        price_tokens=price_tokens,
        labels=_normalize_pack_labels(labels),
        sort_order=0,
    )
    db.add(pack)
    db.flush()
    return pack


def patch_studio_pack(
    db: Session,
    *,
    user: User,
    pack_id: uuid.UUID,
    labels: dict[str, Any] | None = None,
    price_tokens: int | None = None,
    cover_icon_id: uuid.UUID | None = None,
    clear_cover: bool = False,
) -> IconPack:
    pack = get_pack_or_raise(db, pack_id)
    _assert_pack_editable(pack, user)
    if labels is not None:
        pack.labels = _normalize_pack_labels(labels)
    if price_tokens is not None:
        if price_tokens < 0:
            raise MarketplaceError(
                "price_tokens must be >= 0",
                code=ErrorCode.INVALID_PACK_LABELS,
            )
        pack.price_tokens = price_tokens
    if clear_cover:
        pack.cover_icon_id = None
    elif cover_icon_id is not None:
        icon = db.scalar(
            select(CatalogIcon).where(
                CatalogIcon.id == cover_icon_id,
                CatalogIcon.pack_id == pack.id,
            )
        )
        if icon is None:
            raise MarketplaceError(
                "Cover icon must belong to this pack",
                code=ErrorCode.COVER_ICON_NOT_IN_PACK,
            )
        pack.cover_icon_id = cover_icon_id
    db.flush()
    return pack


def delete_studio_pack(db: Session, *, user: User, pack_id: uuid.UUID) -> None:
    pack = get_pack_or_raise(db, pack_id)
    _assert_pack_editable(pack, user)
    db.delete(pack)
    db.flush()


def upload_studio_icon(
    db: Session,
    *,
    user: User,
    pack_id: uuid.UUID,
    storage: ObjectStorage,
    data: bytes,
    content_type: str,
    original_name: str,
    labels: dict[str, str],
    suggested_colors: list[str],
    suggested_mood_scores: list[int] | None = None,
    search_tag_slugs: list[str] | None = None,
    slug: str | None = None,
) -> CatalogIcon:
    pack = get_pack_or_raise(db, pack_id)
    _assert_pack_editable(pack, user)
    mime_type = _validate_image_payload(data=data, content_type=content_type)
    icon_id = uuid.uuid4()
    normalized_labels = _normalize_locale_labels(
        labels,
        code=ErrorCode.INVALID_ICON_LABELS,
        field="labels",
    )
    icon_slug = _unique_icon_slug(
        db,
        pack_id=pack.id,
        base=_slugify(slug or resolve_label(normalized_labels, DEFAULT_LOCALE)),
    )
    storage_key = _build_catalog_storage_key(
        pack_id=pack.id,
        icon_id=icon_id,
        original_name=original_name,
    )
    storage.put_object(key=storage_key, data=data, content_type=mime_type)
    tags = _resolve_search_tags(db, slugs=search_tag_slugs)
    sort_order = db.scalar(
        select(func.coalesce(func.max(CatalogIcon.sort_order), -1)).where(
            CatalogIcon.pack_id == pack.id
        )
    )
    icon = CatalogIcon(
        id=icon_id,
        pack_id=pack.id,
        slug=icon_slug,
        labels=normalized_labels,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=len(data),
        suggested_colors=_normalize_suggested_colors(suggested_colors),
        suggested_mood_scores=_normalize_suggested_mood_scores(suggested_mood_scores),
        sort_order=int(sort_order) + 1 if sort_order is not None else 0,
    )
    icon.search_tags = tags
    db.add(icon)
    # Insert the icon before pointing the pack cover at it (FK on cover_icon_id).
    db.flush()
    if pack.cover_icon_id is None:
        pack.cover_icon_id = icon.id
        db.flush()
    return icon


def patch_studio_icon(
    db: Session,
    *,
    user: User,
    icon_id: uuid.UUID,
    labels: dict[str, str] | None = None,
    suggested_colors: list[str] | None = None,
    suggested_mood_scores: list[int] | None = None,
    search_tag_slugs: list[str] | None = None,
    sort_order: int | None = None,
) -> CatalogIcon:
    icon = get_catalog_icon_or_raise(db, icon_id)
    _assert_pack_editable(icon.pack, user)
    if labels is not None:
        icon.labels = _normalize_locale_labels(
            labels,
            code=ErrorCode.INVALID_ICON_LABELS,
            field="labels",
        )
    if suggested_colors is not None:
        icon.suggested_colors = _normalize_suggested_colors(suggested_colors)
    if suggested_mood_scores is not None:
        icon.suggested_mood_scores = _normalize_suggested_mood_scores(suggested_mood_scores)
    if search_tag_slugs is not None:
        icon.search_tags = _resolve_search_tags(db, slugs=search_tag_slugs)
    if sort_order is not None:
        icon.sort_order = sort_order
    db.flush()
    return icon


def delete_studio_icon(
    db: Session,
    *,
    user: User,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> None:
    icon = get_catalog_icon_or_raise(db, icon_id)
    pack = icon.pack
    _assert_pack_editable(pack, user)
    if pack.cover_icon_id == icon.id:
        pack.cover_icon_id = None
    key = icon.storage_key
    db.delete(icon)
    db.flush()
    with contextlib.suppress(StorageError):
        storage.delete_object(key=key)


def submit_studio_pack(db: Session, *, user: User, pack_id: uuid.UUID) -> IconPack:
    pack = get_pack_or_raise(db, pack_id)
    if pack.author_id != user.id and not user.is_staff:
        raise MarketplaceError(
            "Icon pack not found",
            code=ErrorCode.ICON_PACK_NOT_FOUND,
            status_code=404,
        )
    if pack.status not in {PackStatus.DRAFT.value, PackStatus.REJECTED.value}:
        raise MarketplaceError(
            "Only draft or rejected packs can be submitted",
            code=ErrorCode.ICON_PACK_INVALID_STATUS,
            params={"status": pack.status},
        )
    icon_count = db.scalar(
        select(func.count()).select_from(CatalogIcon).where(CatalogIcon.pack_id == pack.id)
    )
    if not icon_count:
        raise MarketplaceError(
            "Pack must contain at least one icon",
            code=ErrorCode.ICON_PACK_EMPTY,
        )
    pack.status = PackStatus.PENDING_REVIEW.value
    pack.moderation_note = None
    db.flush()
    return pack


# --- Staff ---


def list_staff_packs(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[IconPack]:
    query = select(IconPack).order_by(IconPack.updated_at.desc())
    if status:
        if status not in {s.value for s in PackStatus}:
            raise MarketplaceError(
                f"Invalid pack status: {status}",
                code=ErrorCode.ICON_PACK_INVALID_STATUS,
                params={"status": status},
            )
        query = query.where(IconPack.status == status)
    return list(db.scalars(query.limit(limit).offset(offset)).all())


def publish_pack(db: Session, *, staff: User, pack_id: uuid.UUID) -> IconPack:
    pack = get_pack_or_raise(db, pack_id)
    icon_count = db.scalar(
        select(func.count()).select_from(CatalogIcon).where(CatalogIcon.pack_id == pack.id)
    )
    if not icon_count:
        raise MarketplaceError(
            "Pack must contain at least one icon",
            code=ErrorCode.ICON_PACK_EMPTY,
        )
    pack.status = PackStatus.PUBLISHED.value
    pack.published_at = datetime.now(UTC)
    pack.reviewed_at = pack.published_at
    pack.reviewed_by = staff.id
    pack.moderation_note = None
    db.flush()
    return pack


def reject_pack(
    db: Session,
    *,
    staff: User,
    pack_id: uuid.UUID,
    note: str | None = None,
) -> IconPack:
    pack = get_pack_or_raise(db, pack_id)
    if pack.status not in {
        PackStatus.PENDING_REVIEW.value,
        PackStatus.PUBLISHED.value,
        PackStatus.DRAFT.value,
    }:
        raise MarketplaceError(
            f"Cannot reject pack in status {pack.status}",
            code=ErrorCode.ICON_PACK_INVALID_STATUS,
            params={"status": pack.status},
        )
    pack.status = PackStatus.REJECTED.value
    pack.reviewed_at = datetime.now(UTC)
    pack.reviewed_by = staff.id
    pack.moderation_note = (note or "")[:1000] or None
    db.flush()
    return pack


def pack_icon_count(db: Session, pack_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(CatalogIcon).where(CatalogIcon.pack_id == pack_id)
        )
        or 0
    )


def pack_search_tag_slugs(db: Session, pack_id: uuid.UUID) -> list[str]:
    rows = db.execute(
        select(IconSearchTag.slug, IconSearchTag.sort_order)
        .join(CatalogIconSearchTag, CatalogIconSearchTag.tag_id == IconSearchTag.id)
        .join(CatalogIcon, CatalogIcon.id == CatalogIconSearchTag.icon_id)
        .where(CatalogIcon.pack_id == pack_id)
        .distinct()
        .order_by(IconSearchTag.sort_order, IconSearchTag.slug)
    ).all()
    return [slug for slug, _sort_order in rows]


def serialize_search_tag(tag: IconSearchTag, *, locale: str) -> dict[str, Any]:
    return {
        "id": tag.id,
        "slug": tag.slug,
        "label": resolve_label(tag.labels, locale),
        "labels": tag.labels,
        "sort_order": tag.sort_order,
        "is_active": tag.is_active,
    }


def serialize_icon(icon: CatalogIcon, *, locale: str) -> dict[str, Any]:
    return {
        "id": icon.id,
        "pack_id": icon.pack_id,
        "slug": icon.slug,
        "label": resolve_label(icon.labels, locale),
        "labels": icon.labels,
        "mime_type": icon.mime_type,
        "size_bytes": icon.size_bytes,
        "suggested_colors": list(icon.suggested_colors or []),
        "suggested_mood_scores": list(icon.suggested_mood_scores or []),
        "sort_order": icon.sort_order,
        "search_tags": [
            serialize_search_tag(tag, locale=locale) for tag in (icon.search_tags or [])
        ],
    }


def serialize_pack_card(
    db: Session,
    pack: IconPack,
    *,
    user: User,
    locale: str,
) -> dict[str, Any]:
    unlocked = pack.price_tokens == 0 or _pack_is_unlocked(db, user_id=user.id, pack_id=pack.id)
    name_labels = (pack.labels or {}).get("name") or {}
    description_labels = (pack.labels or {}).get("description") or {}
    return {
        "id": pack.id,
        "slug": pack.slug,
        "name": resolve_label(name_labels, locale) if name_labels else pack.slug,
        "description": resolve_label(description_labels, locale) if description_labels else "",
        "labels": pack.labels,
        "is_official": pack.is_official,
        "status": pack.status,
        "price_tokens": pack.price_tokens,
        "unlocked": unlocked,
        "icon_count": pack_icon_count(db, pack.id),
        "cover_icon_id": pack.cover_icon_id,
        "search_tags": pack_search_tag_slugs(db, pack.id),
        "sort_order": pack.sort_order,
        "published_at": pack.published_at,
        "author_id": pack.author_id,
        "moderation_note": pack.moderation_note,
    }


# Silence unused import warning for ESSENTIALS used by seed module
__all__ = [
    "ESSENTIALS_PACK_SLUG",
    "MarketplaceError",
    "can_assign_catalog_icon",
    "create_search_tag",
    "create_studio_pack",
    "delete_search_tag",
    "delete_studio_icon",
    "delete_studio_pack",
    "download_catalog_icon",
    "get_catalog_icon_or_raise",
    "get_pack_by_ref",
    "get_pack_detail",
    "get_pack_or_raise",
    "list_published_packs",
    "list_search_tags",
    "list_staff_packs",
    "list_user_unlocks",
    "pack_icon_count",
    "patch_studio_icon",
    "patch_studio_pack",
    "publish_pack",
    "reject_pack",
    "revoke_pack_unlock",
    "search_icons",
    "serialize_icon",
    "serialize_pack_card",
    "serialize_search_tag",
    "submit_studio_pack",
    "unlock_pack",
    "update_search_tag",
    "upload_studio_icon",
    "user_can_assign_catalog_icon",
    "user_can_view_pack",
]
