import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale
from app.db.session import get_db
from app.models.note_template import NoteTemplate
from app.models.user import User
from app.schemas.note_template import (
    NoteTemplateCreate,
    NoteTemplateListResponse,
    NoteTemplatePatch,
    NoteTemplatePublic,
    NoteTemplateReorderRequest,
)
from app.services.note_template_service import (
    NoteTemplateError,
    create_note_template,
    delete_note_template,
    list_note_templates,
    patch_note_template,
    reorder_note_templates,
    serialize_note_template,
    serialize_note_templates,
)

router = APIRouter(tags=["note-templates"])


def _handle_error(exc: NoteTemplateError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _to_public(template: NoteTemplate, *, locale: str) -> NoteTemplatePublic:
    return NoteTemplatePublic.model_validate(serialize_note_template(template, locale=locale))


def _to_list_response(templates: list[NoteTemplate], *, locale: str) -> NoteTemplateListResponse:
    items = [
        NoteTemplatePublic.model_validate(item)
        for item in serialize_note_templates(templates, locale=locale)
    ]
    return NoteTemplateListResponse(items=items)


@router.get("", response_model=NoteTemplateListResponse)
def get_note_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> NoteTemplateListResponse:
    templates = list_note_templates(db, user_id=current_user.id)
    return _to_list_response(templates, locale=locale)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=NoteTemplatePublic)
def create_template(
    body: NoteTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> NoteTemplatePublic:
    try:
        template = create_note_template(
            db,
            user_id=current_user.id,
            labels=body.labels,
            bodies=body.bodies,
            slug=body.slug,
            sort_order=body.sort_order,
        )
    except NoteTemplateError as exc:
        _handle_error(exc)
        raise
    return _to_public(template, locale=locale)


@router.put("/reorder", response_model=NoteTemplateListResponse)
def reorder_templates(
    body: NoteTemplateReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> NoteTemplateListResponse:
    try:
        templates = reorder_note_templates(
            db,
            user_id=current_user.id,
            ordered_ids=body.ordered_ids,
        )
    except NoteTemplateError as exc:
        _handle_error(exc)
        raise
    return _to_list_response(templates, locale=locale)


@router.patch("/{template_id}", response_model=NoteTemplatePublic)
def update_template(
    template_id: uuid.UUID,
    body: NoteTemplatePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> NoteTemplatePublic:
    try:
        template = patch_note_template(
            db,
            user_id=current_user.id,
            template_id=template_id,
            slug=body.slug,
            labels=body.labels,
            bodies=body.bodies,
            sort_order=body.sort_order,
        )
    except NoteTemplateError as exc:
        _handle_error(exc)
        raise
    return _to_public(template, locale=locale)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    try:
        delete_note_template(db, user_id=current_user.id, template_id=template_id)
    except NoteTemplateError as exc:
        _handle_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
