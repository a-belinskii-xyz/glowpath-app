import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale
from app.config import settings
from app.db.session import get_db
from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.models.user import User
from app.schemas.tag import (
    TagCreate,
    TagGroupCreate,
    TagGroupListResponse,
    TagGroupPatch,
    TagGroupPublic,
    TagGroupReorderRequest,
    TagPatch,
    TagPublic,
    TagReorderRequest,
)
from app.services.tag_service import (
    TagError,
    create_tag,
    create_tag_group,
    delete_tag,
    delete_tag_group,
    list_tag_groups,
    patch_tag,
    patch_tag_group,
    reorder_tag_groups,
    reorder_tags,
    serialize_tag,
    serialize_tag_group,
    serialize_tag_groups,
)

router = APIRouter(tags=["tag-groups"])


def _handle_tag_error(exc: TagError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _to_group_public(group: TagGroup, *, locale: str) -> TagGroupPublic:
    return TagGroupPublic.model_validate(serialize_tag_group(group, locale=locale))


def _to_tag_public(tag: Tag, *, locale: str) -> TagPublic:
    return TagPublic.model_validate(serialize_tag(tag, locale=locale))


def _to_list_response(groups: list[TagGroup], *, locale: str) -> TagGroupListResponse:
    items = [
        TagGroupPublic.model_validate(item) for item in serialize_tag_groups(groups, locale=locale)
    ]
    return TagGroupListResponse(
        items=items,
        entry_visible_tag_group_limit=settings.entry_visible_tag_group_limit,
    )


@router.get("", response_model=TagGroupListResponse)
def get_tag_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> TagGroupListResponse:
    groups = list_tag_groups(db, user_id=current_user.id)
    return _to_list_response(groups, locale=locale)


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
    return _to_list_response(groups, locale=locale)


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
        tag = create_tag(
            db,
            user_id=current_user.id,
            group_id=group_id,
            slug=body.slug,
            labels=body.labels,
            sort_order=body.sort_order,
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
        tag = patch_tag(
            db,
            user_id=current_user.id,
            group_id=group_id,
            tag_id=tag_id,
            slug=body.slug,
            labels=body.labels,
            sort_order=body.sort_order,
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
