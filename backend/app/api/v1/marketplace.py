"""Icon marketplace API: storefront, studio, and staff moderation."""

from __future__ import annotations

import json
import uuid
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale, get_storage_service
from app.core.error_codes import ErrorCode
from app.core.errors import raise_http_error, structured_detail
from app.core.feature_flags import FeatureFlag, is_feature_enabled_for_user
from app.core.marketplace import ICON_CROP_HEADER, ICON_CROP_KEYS
from app.db.session import get_db
from app.models.user import User
from app.schemas.marketplace import (
    CatalogIconPublic,
    CatalogIconWithPackPublic,
    IconListResponse,
    IconOrderBody,
    PackCardPublic,
    PackDetailPublic,
    PackListResponse,
    PackUnlockListResponse,
    PackUnlockPublic,
    RejectPackBody,
    SearchTagCreate,
    SearchTagListResponse,
    SearchTagPatch,
    SearchTagPublic,
    StudioIconPatch,
    StudioPackCreate,
    StudioPackPatch,
)
from app.services.marketplace_service import (
    MarketplaceError,
    create_search_tag,
    create_studio_pack,
    delete_search_tag,
    delete_studio_icon,
    delete_studio_pack,
    download_catalog_icon,
    get_catalog_icon_or_raise,
    get_pack_detail,
    list_published_packs,
    list_search_tags,
    list_staff_packs,
    list_user_unlocks,
    patch_studio_icon,
    patch_studio_pack,
    publish_pack,
    reject_pack,
    reorder_studio_icons,
    replace_studio_icon_image,
    search_icons,
    serialize_icon,
    serialize_pack_card,
    serialize_search_tag,
    submit_studio_pack,
    unlock_pack,
    update_search_tag,
    upload_studio_icon,
)
from app.services.storage import ObjectStorage, StorageError

router = APIRouter(tags=["marketplace"])


def _handle_marketplace_error(exc: MarketplaceError) -> None:
    raise_http_error(exc)


def _handle_storage_error(exc: StorageError) -> None:
    raise_http_error(exc)


def _require_marketplace(user: User) -> None:
    if not is_feature_enabled_for_user(FeatureFlag.ICON_MARKETPLACE, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=structured_detail(
                code=ErrorCode.MARKETPLACE_DISABLED,
                message="Icon marketplace is not enabled for this user",
            ),
        )


def _require_staff(user: User) -> None:
    if not user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=structured_detail(
                code=ErrorCode.STAFF_REQUIRED,
                message="Staff access required",
            ),
        )


def _parse_json_form(raw: str | None, *, default: object) -> object:
    if raw is None or raw.strip() == "":
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=structured_detail(
                code=ErrorCode.INVALID_ICON_LABELS,
                message="Invalid JSON form field",
            ),
        ) from exc


@router.get("/search-tags", response_model=SearchTagListResponse)
def get_search_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> SearchTagListResponse:
    _require_marketplace(current_user)
    items = [
        SearchTagPublic.model_validate(serialize_search_tag(tag, locale=locale))
        for tag in list_search_tags(db, active_only=True)
    ]
    return SearchTagListResponse(items=items)


@router.get("/packs", response_model=PackListResponse)
def get_packs(
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    official: bool | None = Query(default=None),
    unlocked: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackListResponse:
    _require_marketplace(current_user)
    packs = list_published_packs(
        db,
        user=current_user,
        q=q,
        tag=tag,
        official=official,
        unlocked=unlocked,
        limit=limit,
        offset=offset,
    )
    return PackListResponse(
        items=[
            PackCardPublic.model_validate(
                serialize_pack_card(db, pack, user=current_user, locale=locale)
            )
            for pack in packs
        ]
    )


@router.get("/packs/{pack_id}", response_model=PackDetailPublic)
def get_pack(
    pack_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    _require_marketplace(current_user)
    try:
        pack = get_pack_detail(db, user=current_user, pack_id=pack_id)
    except MarketplaceError as exc:
        _handle_marketplace_error(exc)
        raise
    card = serialize_pack_card(db, pack, user=current_user, locale=locale)
    card["icons"] = [serialize_icon(icon, locale=locale) for icon in pack.icons]
    return PackDetailPublic.model_validate(card)


@router.post("/packs/{pack_id}/unlock", response_model=PackUnlockPublic)
def post_unlock_pack(
    pack_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackUnlockPublic:
    _require_marketplace(current_user)
    try:
        unlock = unlock_pack(db, user=current_user, pack_id=pack_id)
        unlocked_at = unlock.unlocked_at
        unlock_pack_id = unlock.pack_id
        db.commit()
        pack = get_pack_detail(db, user=current_user, pack_id=pack_id)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    return PackUnlockPublic(
        pack_id=unlock_pack_id,
        unlocked_at=unlocked_at,
        pack=PackCardPublic.model_validate(
            serialize_pack_card(db, pack, user=current_user, locale=locale)
        ),
    )


@router.get("/me/unlocks", response_model=PackUnlockListResponse)
def get_my_unlocks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackUnlockListResponse:
    _require_marketplace(current_user)
    items: list[PackUnlockPublic] = []
    for unlock in list_user_unlocks(db, user_id=current_user.id):
        pack_card = None
        if unlock.pack is not None:
            pack_card = PackCardPublic.model_validate(
                serialize_pack_card(db, unlock.pack, user=current_user, locale=locale)
            )
        items.append(
            PackUnlockPublic(
                pack_id=unlock.pack_id,
                unlocked_at=unlock.unlocked_at,
                pack=pack_card,
            )
        )
    return PackUnlockListResponse(items=items)


@router.get("/icons", response_model=IconListResponse)
def get_icons(
    q: str | None = Query(default=None),
    tag: list[str] | None = Query(default=None),
    pack_id: uuid.UUID | None = Query(default=None),
    suggested_mood: int | None = Query(default=None, ge=1, le=5),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> IconListResponse:
    _require_marketplace(current_user)
    try:
        icons = search_icons(
            db,
            user=current_user,
            q=q,
            tags=tag,
            pack_id=pack_id,
            suggested_mood=suggested_mood,
            limit=limit,
            offset=offset,
        )
    except MarketplaceError as exc:
        _handle_marketplace_error(exc)
        raise
    items: list[CatalogIconWithPackPublic] = []
    for icon in icons:
        payload = serialize_icon(icon, locale=locale)
        payload["pack"] = serialize_pack_card(db, icon.pack, user=current_user, locale=locale)
        items.append(CatalogIconWithPackPublic.model_validate(payload))
    return IconListResponse(items=items)


@router.get("/icons/{icon_id}", response_model=CatalogIconWithPackPublic)
def get_icon(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> CatalogIconWithPackPublic:
    _require_marketplace(current_user)
    try:
        icon = get_catalog_icon_or_raise(db, icon_id)
        from app.services.marketplace_service import user_can_view_pack

        if not user_can_view_pack(current_user, icon.pack):
            raise MarketplaceError(
                "Catalog icon not found",
                code=ErrorCode.CATALOG_ICON_NOT_FOUND,
                status_code=404,
            )
    except MarketplaceError as exc:
        _handle_marketplace_error(exc)
        raise
    payload = serialize_icon(icon, locale=locale)
    payload["pack"] = serialize_pack_card(db, icon.pack, user=current_user, locale=locale)
    return CatalogIconWithPackPublic.model_validate(payload)


@router.get("/icons/{icon_id}/image")
def get_icon_image(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> Response:
    _require_marketplace(current_user)
    try:
        icon, data = download_catalog_icon(db, user=current_user, icon_id=icon_id, storage=storage)
    except MarketplaceError as exc:
        _handle_marketplace_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise
    filename = quote(f"{icon.slug}.{icon.mime_type.split('/')[-1]}")
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    if icon.crop:
        # Clients render only this frame; the stored file stays uncropped.
        headers[ICON_CROP_HEADER] = ",".join(str(icon.crop[key]) for key in ICON_CROP_KEYS)
    return Response(content=data, media_type=icon.mime_type, headers=headers)


# --- Studio ---


@router.post(
    "/studio/packs",
    status_code=status.HTTP_201_CREATED,
    response_model=PackDetailPublic,
)
def post_studio_pack(
    body: StudioPackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    _require_marketplace(current_user)
    try:
        pack = create_studio_pack(
            db,
            user=current_user,
            labels=body.labels.model_dump(exclude_none=True),
            slug=body.slug,
            price_tokens=body.price_tokens,
        )
        db.commit()
        db.refresh(pack)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    card = serialize_pack_card(db, pack, user=current_user, locale=locale)
    card["icons"] = []
    return PackDetailPublic.model_validate(card)


@router.patch("/studio/packs/{pack_id}", response_model=PackDetailPublic)
def patch_studio_pack_endpoint(
    pack_id: uuid.UUID,
    body: StudioPackPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    _require_marketplace(current_user)
    try:
        pack = patch_studio_pack(
            db,
            user=current_user,
            pack_id=pack_id,
            labels=body.labels.model_dump(exclude_none=True) if body.labels else None,
            price_tokens=body.price_tokens,
            cover_icon_id=body.cover_icon_id,
            clear_cover=body.clear_cover,
        )
        db.commit()
        pack = get_pack_detail(db, user=current_user, pack_id=pack.id)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    card = serialize_pack_card(db, pack, user=current_user, locale=locale)
    card["icons"] = [serialize_icon(icon, locale=locale) for icon in pack.icons]
    return PackDetailPublic.model_validate(card)


@router.delete("/studio/packs/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_studio_pack_endpoint(
    pack_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    _require_marketplace(current_user)
    try:
        delete_studio_pack(db, user=current_user, pack_id=pack_id)
        db.commit()
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/studio/packs/{pack_id}/icons",
    status_code=status.HTTP_201_CREATED,
    response_model=CatalogIconPublic,
)
async def post_studio_icon(
    pack_id: uuid.UUID,
    file: UploadFile = File(),
    labels: str = Form(...),
    suggested_colors: str = Form(...),
    suggested_mood_scores: str | None = Form(None),
    suggested_usage: str | None = Form(None),
    search_tag_slugs: str | None = Form(None),
    slug: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
    locale: str = Depends(get_locale),
) -> CatalogIconPublic:
    _require_marketplace(current_user)
    data = await file.read()
    labels_obj = _parse_json_form(labels, default={})
    colors_obj = _parse_json_form(suggested_colors, default=[])
    scores_obj = _parse_json_form(suggested_mood_scores, default=None)
    usage_obj = _parse_json_form(suggested_usage, default=None)
    tags_obj = _parse_json_form(search_tag_slugs, default=None)
    try:
        icon = upload_studio_icon(
            db,
            user=current_user,
            pack_id=pack_id,
            storage=storage,
            data=data,
            content_type=file.content_type or "application/octet-stream",
            original_name=file.filename or "icon",
            labels=labels_obj,  # type: ignore[arg-type]
            suggested_colors=colors_obj,  # type: ignore[arg-type]
            suggested_mood_scores=scores_obj,  # type: ignore[arg-type]
            suggested_usage=usage_obj,  # type: ignore[arg-type]
            search_tag_slugs=tags_obj,  # type: ignore[arg-type]
            slug=slug,
        )
        db.commit()
        icon = get_catalog_icon_or_raise(db, icon.id)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    except StorageError as exc:
        db.rollback()
        _handle_storage_error(exc)
        raise
    return CatalogIconPublic.model_validate(serialize_icon(icon, locale=locale))


@router.patch("/studio/icons/{icon_id}", response_model=CatalogIconPublic)
def patch_studio_icon_endpoint(
    icon_id: uuid.UUID,
    body: StudioIconPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> CatalogIconPublic:
    _require_marketplace(current_user)
    try:
        icon = patch_studio_icon(
            db,
            user=current_user,
            icon_id=icon_id,
            labels=body.labels,
            suggested_colors=body.suggested_colors,
            suggested_mood_scores=body.suggested_mood_scores,
            suggested_usage=body.suggested_usage,
            search_tag_slugs=body.search_tag_slugs,
            sort_order=body.sort_order,
            crop=body.crop.model_dump() if body.crop else None,
            clear_crop=body.clear_crop,
        )
        db.commit()
        icon = get_catalog_icon_or_raise(db, icon.id)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    return CatalogIconPublic.model_validate(serialize_icon(icon, locale=locale))


@router.put("/studio/icons/{icon_id}/image", response_model=CatalogIconPublic)
async def put_studio_icon_image(
    icon_id: uuid.UUID,
    file: UploadFile = File(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
    locale: str = Depends(get_locale),
) -> CatalogIconPublic:
    _require_marketplace(current_user)
    data = await file.read()
    try:
        icon = replace_studio_icon_image(
            db,
            user=current_user,
            icon_id=icon_id,
            storage=storage,
            data=data,
            content_type=file.content_type or "application/octet-stream",
            original_name=file.filename or "icon",
        )
        db.commit()
        icon = get_catalog_icon_or_raise(db, icon.id)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    except StorageError as exc:
        db.rollback()
        _handle_storage_error(exc)
        raise
    return CatalogIconPublic.model_validate(serialize_icon(icon, locale=locale))


@router.put("/studio/packs/{pack_id}/icon-order", response_model=PackDetailPublic)
def put_studio_icon_order(
    pack_id: uuid.UUID,
    body: IconOrderBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    _require_marketplace(current_user)
    try:
        pack = reorder_studio_icons(db, user=current_user, pack_id=pack_id, icon_ids=body.icon_ids)
        db.commit()
        pack = get_pack_detail(db, user=current_user, pack_id=pack.id)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    card = serialize_pack_card(db, pack, user=current_user, locale=locale)
    card["icons"] = [serialize_icon(icon, locale=locale) for icon in pack.icons]
    return PackDetailPublic.model_validate(card)


@router.delete("/studio/icons/{icon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_studio_icon_endpoint(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> Response:
    _require_marketplace(current_user)
    try:
        delete_studio_icon(db, user=current_user, icon_id=icon_id, storage=storage)
        db.commit()
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/studio/packs/{pack_id}/submit", response_model=PackDetailPublic)
def post_submit_pack(
    pack_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    _require_marketplace(current_user)
    try:
        pack = submit_studio_pack(db, user=current_user, pack_id=pack_id)
        db.commit()
        pack = get_pack_detail(db, user=current_user, pack_id=pack.id)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    card = serialize_pack_card(db, pack, user=current_user, locale=locale)
    card["icons"] = [serialize_icon(icon, locale=locale) for icon in pack.icons]
    return PackDetailPublic.model_validate(card)


# --- Staff ---


@router.get("/staff/packs", response_model=PackListResponse)
def get_staff_packs(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackListResponse:
    _require_marketplace(current_user)
    _require_staff(current_user)
    try:
        packs = list_staff_packs(db, status=status_filter, limit=limit, offset=offset)
    except MarketplaceError as exc:
        _handle_marketplace_error(exc)
        raise
    return PackListResponse(
        items=[
            PackCardPublic.model_validate(
                serialize_pack_card(db, pack, user=current_user, locale=locale)
            )
            for pack in packs
        ]
    )


@router.post("/staff/packs/{pack_id}/publish", response_model=PackDetailPublic)
def post_publish_pack(
    pack_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    _require_marketplace(current_user)
    _require_staff(current_user)
    try:
        pack = publish_pack(db, staff=current_user, pack_id=pack_id)
        db.commit()
        pack = get_pack_detail(db, user=current_user, pack_id=pack.id)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    card = serialize_pack_card(db, pack, user=current_user, locale=locale)
    card["icons"] = [serialize_icon(icon, locale=locale) for icon in pack.icons]
    return PackDetailPublic.model_validate(card)


@router.post("/staff/packs/{pack_id}/reject", response_model=PackDetailPublic)
def post_reject_pack(
    pack_id: uuid.UUID,
    body: RejectPackBody | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> PackDetailPublic:
    _require_marketplace(current_user)
    _require_staff(current_user)
    try:
        pack = reject_pack(
            db,
            staff=current_user,
            pack_id=pack_id,
            note=body.note if body else None,
        )
        db.commit()
        pack = get_pack_detail(db, user=current_user, pack_id=pack.id)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    card = serialize_pack_card(db, pack, user=current_user, locale=locale)
    card["icons"] = [serialize_icon(icon, locale=locale) for icon in pack.icons]
    return PackDetailPublic.model_validate(card)


@router.post(
    "/staff/search-tags",
    status_code=status.HTTP_201_CREATED,
    response_model=SearchTagPublic,
)
def post_search_tag(
    body: SearchTagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> SearchTagPublic:
    _require_marketplace(current_user)
    _require_staff(current_user)
    try:
        tag = create_search_tag(
            db,
            slug=body.slug,
            labels=body.labels,
            sort_order=body.sort_order,
            is_active=body.is_active,
        )
        db.commit()
        db.refresh(tag)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    return SearchTagPublic.model_validate(serialize_search_tag(tag, locale=locale))


@router.patch("/staff/search-tags/{tag_id}", response_model=SearchTagPublic)
def patch_search_tag(
    tag_id: uuid.UUID,
    body: SearchTagPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> SearchTagPublic:
    _require_marketplace(current_user)
    _require_staff(current_user)
    try:
        tag = update_search_tag(
            db,
            tag_id=tag_id,
            labels=body.labels,
            sort_order=body.sort_order,
            is_active=body.is_active,
        )
        db.commit()
        db.refresh(tag)
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    return SearchTagPublic.model_validate(serialize_search_tag(tag, locale=locale))


@router.delete("/staff/search-tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_search_tag_endpoint(
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    _require_marketplace(current_user)
    _require_staff(current_user)
    try:
        delete_search_tag(db, tag_id=tag_id)
        db.commit()
    except MarketplaceError as exc:
        db.rollback()
        _handle_marketplace_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
