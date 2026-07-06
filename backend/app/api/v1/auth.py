from typing import cast

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_email_service
from app.config import settings
from app.core.google_oauth import oauth
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    EmailRequest,
    GoogleIdTokenRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserPublic
from app.services.auth_service import (
    AuthError,
    GoogleProfile,
    TokenPair,
    authenticate_google_profile,
    forgot_password,
    login_user,
    refresh_access_token,
    register_user,
    resend_verification_email,
    reset_password,
    verify_email,
    verify_google_id_token,
)
from app.services.email_service import EmailService

router = APIRouter(tags=["auth"])


def _to_user_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        timezone=user.timezone,
        email_verified=user.email_verified_at is not None,
        email_verified_at=user.email_verified_at,
    )


def _handle_auth_error(exc: AuthError) -> None:
    from fastapi import HTTPException

    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _to_token_response(tokens: TokenPair) -> TokenResponse:
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
    mailer: EmailService = Depends(get_email_service),
) -> MessageResponse:
    try:
        register_user(
            db,
            email=body.email,
            password=body.password,
            timezone=body.timezone,
            email_service=mailer,
        )
    except AuthError as exc:
        _handle_auth_error(exc)
    return MessageResponse(message="Check your email to verify your account")


@router.get("/verify-email", response_class=HTMLResponse)
def verify_email_endpoint(
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


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_verification_endpoint(
    body: EmailRequest,
    db: Session = Depends(get_db),
    mailer: EmailService = Depends(get_email_service),
) -> Response:
    resend_verification_email(db, email=body.email, email_service=mailer)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        tokens = login_user(db, email=body.email, password=body.password)
    except AuthError as exc:
        _handle_auth_error(exc)
    return _to_token_response(tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        tokens = refresh_access_token(db, refresh_token=body.refresh_token)
    except AuthError as exc:
        _handle_auth_error(exc)
    return _to_token_response(tokens)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password_endpoint(
    body: EmailRequest,
    db: Session = Depends(get_db),
    mailer: EmailService = Depends(get_email_service),
) -> Response:
    forgot_password(db, email=body.email, email_service=mailer)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password_endpoint(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        reset_password(db, token=body.token, new_password=body.new_password)
    except AuthError as exc:
        _handle_auth_error(exc)
    return MessageResponse(message="Password reset successfully")


@router.get("/google/login")
async def google_login(request: Request) -> Response:
    if not settings.google_client_id or not settings.google_client_secret:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    return cast(
        Response,
        await oauth.google.authorize_redirect(request, settings.google_redirect_uri),
    )


@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    from fastapi import HTTPException

    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Google authorization failed") from exc

    user_info = token.get("userinfo")
    if not isinstance(user_info, dict):
        raise HTTPException(status_code=400, detail="Google user info missing")

    sub = user_info.get("sub")
    email = user_info.get("email")
    if not isinstance(sub, str) or not isinstance(email, str):
        raise HTTPException(status_code=400, detail="Google user info incomplete")

    profile = GoogleProfile(
        sub=sub,
        email=email,
        email_verified=bool(user_info.get("email_verified")),
    )
    try:
        tokens = authenticate_google_profile(db, profile)
    except AuthError as exc:
        _handle_auth_error(exc)
    return _to_token_response(tokens)


@router.post("/google", response_model=TokenResponse)
def google_id_token_login(
    body: GoogleIdTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        profile = verify_google_id_token(body.id_token)
        tokens = authenticate_google_profile(db, profile)
    except AuthError as exc:
        _handle_auth_error(exc)
    return _to_token_response(tokens)


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return _to_user_public(current_user)
