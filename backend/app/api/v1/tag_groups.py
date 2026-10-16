import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale, get_storage_service
from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.models.user import User
from app.models.user_tag_icon import UserTagIcon
from app.schemas.tag import (
    QuickTagCreate,
    QuickTagResponse,
    TagCreate,
    TagGroupCreate,
    TagGroupListResponse,
    TagGroupPatch,
    TagGroupPublic,
    TagGroupReorderRequest,
    TagIconListResponse,
    TagIconMetaPublic,
    TagIconPublic,
    TagPatch,
    TagPublic,
    TagReorderRequest,
)
from app.services.storage import ObjectStorage, StorageError
from app.services.tag_icon_service import (
    MAX_ICONS_PER_TAG,
    TagIconError,
    delete_tag_icon_by_id,
    download_tag_icon,
    download_tag_icon_source,
    list_tag_icons,
    upload_tag_icon,
)
from app.services.tag_service import (
    TagError,
    create_tag,
    create_tag_group,
    delete_tag,
    delete_tag_group,
    ensure_unique_tag_label,
    get_owned_tag,
    list_tag_groups,
    patch_tag,
    patch_tag_group,
    quick_create_tag,
    reorder_tag_groups,
    reorder_tags,
    serialize_frequent_tags,
    serialize_tag,
    serialize_tag_group,
    serialize_tag_groups,
    tag_label_key,
)

router = APIRouter(tags=["tag-groups"])


def _handle_tag_error(exc: TagError) -> None:
    raise_http_error(exc)


def _handle_icon_error(exc: TagIconError) -> None:
    raise_http_error(exc)


def _handle_storage_error(exc: StorageError) -> None:
    raise_http_error(exc)


def _to_group_public(group: TagGroup, *, locale: str) -> TagGroupPublic:
    return TagGroupPublic.model_validate(serialize_tag_group(group, locale=locale))


def _to_tag_public(tag: Tag, *, locale: str) -> TagPublic:
    return TagPublic.model_validate(serialize_tag(tag, locale=locale))


def _to_list_response(
    groups: list[TagGroup],
    *,
    locale: str,
    user: User,
    db: Session,
) -> TagGroupListResponse:
    items = [
        TagGroupPublic.model_validate(item) for item in serialize_tag_groups(groups, locale=locale)
    ]
    frequent = serialize_frequent_tags(db, user=user, locale=locale)
    return TagGroupListResponse(
        items=items,
        entry_visible_tag_group_limit=settings.entry_visible_tag_group_limit,
        frequent_tags=[TagPublic.model_validate(item) for item in frequent],
    )


def _icon_meta(icon: UserTagIcon) -> TagIconMetaPublic:
    return TagIconMetaPublic(
        id=icon.id,
        tag_id=icon.tag_id,
        mime_type=icon.mime_type,
        size_bytes=icon.size_bytes,
        original_name=icon.original_name,
        has_source=bool(icon.source_storage_key),
    )


def _ensure_tag_in_group(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> Tag:
    tag = get_owned_tag(db, user_id=user_id, tag_id=tag_id)
    if tag.group_id != group_id:
        raise TagError(
            "Tag not found in this group", code=ErrorCode.TAG_NOT_FOUND_IN_GROUP, status_code=404
        )
    return tag


@router.get("", response_model=TagGroupListResponse)
def get_tag_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> TagGroupListResponse:
    groups = list_tag_groups(db, user_id=current_user.id)
    return _to_list_response(groups, locale=locale, user=current_user, db=db)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TagGroupPublic)
def create_group(
    body: TagGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> TagGroupPublic:
    try:
        group = create_tag_group(
            db,
            user_id=current_user.id,
            slug=body.slug,
            labels=body.labels,
            sort_order=body.sort_order,
            show_on_entry=body.show_on_entry,
        )
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    return _to_group_public(group, locale=locale)


@router.post("/quick-tag", response_model=QuickTagResponse)
def create_quick_tag(
    body: QuickTagCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> QuickTagResponse:
    """Tag typed in the entry form: reuse the user's tag with this name or add it to «New tags»."""
    tag, created = quick_create_tag(db, user_id=current_user.id, label=body.label, locale=locale)
    if created:
        response.status_code = status.HTTP_201_CREATED
    return QuickTagResponse(tag=_to_tag_public(tag, locale=locale), created=created)


@router.put("/reorder", response_model=TagGroupListResponse)
def reorder_groups(
    body: TagGroupReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> TagGroupListResponse:
    try:
        groups = reorder_tag_groups(
            db,
            user_id=current_user.id,
            ordered_ids=body.ordered_ids,
        )
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    return _to_list_response(groups, locale=locale, user=current_user, db=db)


@router.get("/icons/id/{icon_id}")
def download_tag_icon_endpoint(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> FastAPIResponse:
    try:
        icon, data = download_tag_icon(
            db,
            user_id=current_user.id,
            icon_id=icon_id,
            storage=storage,
        )
    except TagIconError as exc:
        _handle_icon_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise

    filename = quote(icon.original_name)
    return FastAPIResponse(
        content=data,
        media_type=icon.mime_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{filename}"},
    )


@router.get("/icons/id/{icon_id}/source")
def download_tag_icon_source_endpoint(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> FastAPIResponse:
    try:
        icon, data = download_tag_icon_source(
            db,
            user_id=current_user.id,
            icon_id=icon_id,
            storage=storage,
        )
    except TagIconError as exc:
        _handle_icon_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise

    filename = quote(icon.original_name)
    return FastAPIResponse(
        content=data,
        media_type=icon.source_mime_type or "application/octet-stream",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{filename}"},
    )


@router.delete(
    "/icons/id/{icon_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_tag_icon_endpoint(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> Response:
    try:
        delete_tag_icon_by_id(
            db,
            user_id=current_user.id,
            icon_id=icon_id,
            storage=storage,
        )
    except TagIconError as exc:
        _handle_icon_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{group_id}", response_model=TagGroupPublic)
def update_group(
    group_id: uuid.UUID,
    body: TagGroupPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> TagGroupPublic:
    try:
        group = patch_tag_group(
            db,
            user_id=current_user.id,
            group_id=group_id,
            slug=body.slug,
            labels=body.labels,
            sort_order=body.sort_order,
            show_on_entry=body.show_on_entry,
        )
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    return _to_group_public(group, locale=locale)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_group(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    try:
        delete_tag_group(db, user_id=current_user.id, group_id=group_id)
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{group_id}/tags",
    status_code=status.HTTP_201_CREATED,
    response_model=TagPublic,
)
def create_group_tag(
    group_id: uuid.UUID,
    body: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> TagPublic:
    try:
        ensure_unique_tag_label(db, user_id=current_user.id, labels=body.labels)
        tag = create_tag(
            db,
            user_id=current_user.id,
            group_id=group_id,
            slug=body.slug,
            labels=body.labels,
            sort_order=body.sort_order,
            color=body.color,
            icon_type=body.icon_type.value if body.icon_type is not None else None,
            icon=body.icon,
        )
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    return _to_tag_public(tag, locale=locale)


@router.put("/{group_id}/tags/reorder", response_model=TagGroupPublic)
def reorder_group_tags(
    group_id: uuid.UUID,
    body: TagReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> TagGroupPublic:
    try:
        group = reorder_tags(
            db,
            user_id=current_user.id,
            group_id=group_id,
            ordered_ids=body.ordered_ids,
        )
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    return _to_group_public(group, locale=locale)


@router.get("/{group_id}/tags/{tag_id}/icons", response_model=TagIconListResponse)
def list_tag_icons_endpoint(
    group_id: uuid.UUID,
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> TagIconListResponse:
    try:
        _ensure_tag_in_group(
            db,
            user_id=current_user.id,
            group_id=group_id,
            tag_id=tag_id,
        )
        icons = list_tag_icons(db, user_id=current_user.id, tag_id=tag_id)
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    return TagIconListResponse(
        items=[_icon_meta(icon) for icon in icons],
        max_per_tag=MAX_ICONS_PER_TAG,
    )


@router.post(
    "/{group_id}/tags/{tag_id}/icons",
    status_code=status.HTTP_201_CREATED,
    response_model=TagIconPublic,
)
async def upload_tag_icon_endpoint(
    group_id: uuid.UUID,
    tag_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    source: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
    locale: str = Depends(get_locale),
) -> TagIconPublic:
    data = await file.read()
    original_name = file.filename or "icon"
    content_type = file.content_type or "application/octet-stream"
    source_data: bytes | None = None
    source_content_type: str | None = None
    source_original_name: str | None = None
    if source is not None:
        source_data = await source.read()
        source_content_type = source.content_type or "application/octet-stream"
        source_original_name = source.filename or original_name
    try:
        _ensure_tag_in_group(
            db,
            user_id=current_user.id,
            group_id=group_id,
            tag_id=tag_id,
        )
        icon, tag = upload_tag_icon(
            db,
            user_id=current_user.id,
            tag_id=tag_id,
            data=data,
            content_type=content_type,
            original_name=original_name,
            storage=storage,
            source_data=source_data,
            source_content_type=source_content_type,
            source_original_name=source_original_name,
        )
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    except TagIconError as exc:
        _handle_icon_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise

    return TagIconPublic(
        id=icon.id,
        tag_id=icon.tag_id,
        mime_type=icon.mime_type,
        size_bytes=icon.size_bytes,
        original_name=icon.original_name,
        has_source=bool(icon.source_storage_key),
        tag=_to_tag_public(tag, locale=locale),
    )


@router.patch("/{group_id}/tags/{tag_id}", response_model=TagPublic)
def update_group_tag(
    group_id: uuid.UUID,
    tag_id: uuid.UUID,
    body: TagPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> TagPublic:
    try:
        if body.labels is not None:
            current = get_owned_tag(db, user_id=current_user.id, tag_id=tag_id)
            renamed = {
                key: value
                for key, value in body.labels.items()
                if tag_label_key(current.labels.get(key, "")) != tag_label_key(value)
            }
            ensure_unique_tag_label(
                db, user_id=current_user.id, labels=renamed, exclude_tag_id=tag_id
            )
        tag = patch_tag(
            db,
            user_id=current_user.id,
            group_id=group_id,
            tag_id=tag_id,
            slug=body.slug,
            labels=body.labels,
            sort_order=body.sort_order,
            color=body.color,
            icon_type=body.icon_type.value if body.icon_type is not None else None,
            icon=body.icon,
            target_group_id=body.group_id,
        )
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    return _to_tag_public(tag, locale=locale)


@router.delete(
    "/{group_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def remove_group_tag(
    group_id: uuid.UUID,
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    try:
        delete_tag(db, user_id=current_user.id, group_id=group_id, tag_id=tag_id)
    except TagError as exc:
        _handle_tag_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
