import html

from fastapi import APIRouter, Depends, Form, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import (
    AuthError,
    reset_password,
    validate_password_reset_token,
    verify_email,
)

router = APIRouter(tags=["auth-dev"])


@router.get("/verify-email", response_class=HTMLResponse)
def verify_email_page(
    token: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        verify_email(db, token=token)
    except AuthError as exc:
        return HTMLResponse(
            content=f"<html><body><p>{exc.message}</p></body></html>",
            status_code=exc.status_code,
        )
    return HTMLResponse(
        content=(
            "<html><body>"
            "<p>Email verified successfully. You can close this page and log in.</p>"
            "</body></html>"
        ),
    )


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(
    token: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        validate_password_reset_token(db, token=token)
    except AuthError as exc:
        return HTMLResponse(
            content=f"<html><body><p>{exc.message}</p></body></html>",
            status_code=exc.status_code,
        )
    return HTMLResponse(
        content=(
            "<html><body>"
            "<h1>Reset your password</h1>"
            '<form method="post" action="/v1/dev/auth/reset-password">'
            f'<input type="hidden" name="token" value="{html.escape(token, quote=True)}">'
            '<p><label>New password: <input type="password" name="new_password" '
            'minlength="8" maxlength="128" required></label></p>'
            '<p><label>Confirm password: <input type="password" name="password_confirm" '
            'minlength="8" maxlength="128" required></label></p>'
            '<p><button type="submit">Reset password</button></p>'
            "</form>"
            "</body></html>"
        ),
    )


@router.post("/reset-password", response_class=HTMLResponse)
def reset_password_form(
    token: str = Form(..., min_length=1),
    new_password: str = Form(..., min_length=8, max_length=128),
    password_confirm: str = Form(..., min_length=8, max_length=128),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    if new_password != password_confirm:
        return HTMLResponse(
            content="<html><body><p>Passwords do not match</p></body></html>",
            status_code=400,
        )
    try:
        reset_password(db, token=token, new_password=new_password)
    except AuthError as exc:
        return HTMLResponse(
            content=f"<html><body><p>{exc.message}</p></body></html>",
            status_code=exc.status_code,
        )
    return HTMLResponse(
        content=(
            "<html><body>"
            "<p>Password reset successfully. You can close this page and log in.</p>"
            "</body></html>"
        ),
    )
