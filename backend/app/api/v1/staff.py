"""Staff console API: user lookup, official packs, and catalog presets."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_staff_user, get_locale, get_storage_service
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.marketplace import (
    PackDetailPublic,
    WalletLedgerEntryPublic,
    WalletLedgerListResponse,
)
from app.schemas.staff import (
    PresetImportResponse,
    StaffMetricsResponse,
    StaffPackCreate,
    StaffPackSortBody,
    StaffSignupSourcePublic,
    StaffUserListResponse,
    StaffUserPublic,
    StaffWeekMetricsPublic,
)
from app.services.marketplace_service import (
    MarketplaceError,
    get_pack_detail,
    serialize_icon,
    serialize_pack_card,
)
from app.services.metrics_service import REGULAR_MIN_DAYS, build_metrics_report
from app.services.preset_service import (
    PresetError,
    export_preset,
    import_preset_archive,
)
from app.services.staff_service import (
    archive_pack,
    create_official_pack,
    search_users,
    set_pack_sort_order,
)
from app.services.storage import ObjectStorage, StorageError
from app.services.wallet_service import list_ledger

router = APIRouter(tags=["staff"])


def _pack_detail(db: Session, *, staff: User, pack_id: uuid.UUID, locale: str) -> PackDetailPublic:
    pack = get_pack_detail(db, user=staff, pack_id=pack_id)
    card = serialize_pack_card(db, pack, user=staff, locale=locale)
    card["icons"] = [serialize_icon(icon, locale=locale) for icon in pack.icons]
    return PackDetailPublic.model_validate(card)


@router.get("/users", response_model=StaffUserListResponse)
def get_users(
    q: str | None = Query(default=None, max_length=320),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _staff: User = Depends(get_current_staff_user),
) -> StaffUserListResponse:
    return StaffUserListResponse(
        items=[
            StaffUserPublic(
                id=user.id,
                email=user.email,
                telegram_linked=user.telegram_linked,
                is_staff=bool(user.is_staff),
                balance=balance,
                created_at=user.created_at,
            )
            for user, balance in search_users(db, q=q, limit=limit)
        ]
    )


@router.get("/metrics", response_model=StaffMetricsResponse)
def get_metrics(
    db: Session = Depends(get_db),
    _staff: User = Depends(get_current_staff_user),
) -> StaffMetricsResponse:
    report = build_metrics_report(db)
    return StaffMetricsResponse(
        generated_at=report.generated_at,
        regular_min_days=REGULAR_MIN_DAYS,
        sources=[
            StaffSignupSourcePublic(
                source=item.source,
                last_7_days=item.last_7_days,
                last_30_days=item.last_30_days,
                total=item.total,
            )
            for item in report.sources
        ],
        weeks=[
            StaffWeekMetricsPublic(
                starts_at=week.starts_at,
                ends_at=week.ends_at,
                signups=week.signups,
                active=week.active,
                regular=week.regular,
            )
            for week in report.weeks
        ],
    )


@router.get("/users/{user_id}/ledger", response_model=WalletLedgerListResponse)
def get_user_ledger(
    user_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _staff: User = Depends(get_current_staff_user),
) -> WalletLedgerListResponse:
    return WalletLedgerListResponse(
        items=[
            WalletLedgerEntryPublic(
                id=entry.id,
                delta=entry.delta,
                balance_after=entry.balance_after,
                kind=entry.kind,
                pack_id=entry.pack_id,
                note=entry.note,
                created_at=entry.created_at,
            )
            for entry in list_ledger(db, user_id=user_id, limit=limit)
        ]
    )


@router.post("/packs", status_code=status.HTTP_201_CREATED, response_model=PackDetailPublic)
def post_official_pack(
    body: StaffPackCreate,
    db: Session = Depends(get_db),
    staff: User = Depends(get_current_staff_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    try:
        pack = create_official_pack(
            db,
            staff=staff,
            labels=body.labels.model_dump(exclude_none=True),
            slug=body.slug,
            price_tokens=body.price_tokens,
            sort_order=body.sort_order,
        )
        db.commit()
        return _pack_detail(db, staff=staff, pack_id=pack.id, locale=locale)
    except MarketplaceError as exc:
        db.rollback()
        raise_http_error(exc)


@router.patch("/packs/{pack_id}/sort", response_model=PackDetailPublic)
def patch_pack_sort(
    pack_id: uuid.UUID,
    body: StaffPackSortBody,
    db: Session = Depends(get_db),
    staff: User = Depends(get_current_staff_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    try:
        set_pack_sort_order(db, pack_id=pack_id, sort_order=body.sort_order)
        db.commit()
        return _pack_detail(db, staff=staff, pack_id=pack_id, locale=locale)
    except MarketplaceError as exc:
        db.rollback()
        raise_http_error(exc)


@router.post("/packs/{pack_id}/archive", response_model=PackDetailPublic)
def post_archive_pack(
    pack_id: uuid.UUID,
    db: Session = Depends(get_db),
    staff: User = Depends(get_current_staff_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    try:
        archive_pack(db, staff=staff, pack_id=pack_id)
        db.commit()
        return _pack_detail(db, staff=staff, pack_id=pack_id, locale=locale)
    except MarketplaceError as exc:
        db.rollback()
        raise_http_error(exc)


@router.get("/presets/export")
def get_preset_export(
    pack_id: list[uuid.UUID] | None = Query(default=None),
    all_official: bool = Query(default=False),
    include_achievements: bool = Query(default=True),
    db: Session = Depends(get_db),
    _staff: User = Depends(get_current_staff_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> Response:
    try:
        data, _manifest = export_preset(
            db,
            storage=storage,
            pack_ids=None if all_official else list(pack_id or []),
            include_achievements=include_achievements,
        )
    except StorageError as exc:
        raise_http_error(exc)
    filename = f"glowpath-preset-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/presets/import", response_model=PresetImportResponse)
async def post_preset_import(
    file: UploadFile = File(),
    db: Session = Depends(get_db),
    _staff: User = Depends(get_current_staff_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> PresetImportResponse:
    data = await file.read()
    try:
        report = import_preset_archive(db, storage=storage, data=data)
        db.commit()
    except (PresetError, StorageError) as exc:
        db.rollback()
        raise_http_error(exc)
    return PresetImportResponse(
        search_tags=report.search_tags,
        packs=report.packs,
        icons=report.icons,
        achievements=report.achievements,
    )
