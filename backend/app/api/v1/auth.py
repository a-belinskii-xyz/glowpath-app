from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_email_service
from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.errors import raise_http_error, structured_detail
from app.core.google_oauth import oauth
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AttachEmailRequest,
    EmailRequest,
    GoogleIdTokenRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetRequestResponse,
    PasswordResetRequestStatus,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TelegramAuthRequest,
    TokenResponse,
    VerificationResendResponse,
    VerificationResendStatus,
)
from app.schemas.user import UserPublic, UserUpdate
from app.services.auth_service import (
    AuthError,
    GoogleProfile,
    TokenPair,
    attach_email,
    authenticate_google_profile,
    forgot_password,
    login_user,
    parse_visitor_id,
    refresh_access_token,
    register_user,
    resend_verification_email,
    reset_password,
    update_user_timezone,
    verify_email,
    verify_google_id_token,
)
from app.services.email_service import EmailService
from app.services.telegram_auth_service import authenticate_telegram_init_data
from app.services.user_public import to_user_public

router = APIRouter(tags=["auth"])


def _to_user_public(user: User) -> UserPublic:
    return to_user_public(user)


def _handle_auth_error(exc: AuthError) -> None:
    raise_http_error(exc)


def _to_token_response(tokens: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        user_created=tokens.user_created or None,
    )


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
            visitor_id=parse_visitor_id(body.visitor_id),
        )
    except AuthError as exc:
        _handle_auth_error(exc)
    return MessageResponse(message="Check your email to verify your account")


@router.post("/attach-email", response_model=UserPublic)
def attach_email_endpoint(
    body: AttachEmailRequest,
    db: Session = Depends(get_db),
    mailer: EmailService = Depends(get_email_service),
    current_user: User = Depends(get_current_user),
) -> UserPublic:
    try:
        user = attach_email(
            db,
            user=current_user,
            email=body.email,
            password=body.password,
            email_service=mailer,
        )
    except AuthError as exc:
        _handle_auth_error(exc)
    return _to_user_public(user)


@router.get("/verify-email", response_model=MessageResponse)
def verify_email_endpoint(
    token: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        verify_email(db, token=token)
    except AuthError as exc:
        _handle_auth_error(exc)
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=VerificationResendResponse)
def resend_verification_endpoint(
    body: EmailRequest,
    db: Session = Depends(get_db),
    mailer: EmailService = Depends(get_email_service),
) -> VerificationResendResponse:
    result = resend_verification_email(db, email=body.email, email_service=mailer)
    return VerificationResendResponse(
        message=result.message,
        status=VerificationResendStatus(result.status),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        tokens = login_user(
            db,
            email=body.email,
            password=body.password,
            visitor_id=parse_visitor_id(body.visitor_id),
        )
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


@router.post("/forgot-password", response_model=PasswordResetRequestResponse)
def forgot_password_endpoint(
    body: EmailRequest,
    db: Session = Depends(get_db),
    mailer: EmailService = Depends(get_email_service),
) -> PasswordResetRequestResponse:
    result = forgot_password(db, email=body.email, email_service=mailer)
    return PasswordResetRequestResponse(
        message=result.message,
        status=PasswordResetRequestStatus(result.status),
    )


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
        raise HTTPException(
            status_code=503,
            detail=structured_detail(
                code=ErrorCode.GOOGLE_OAUTH_NOT_CONFIGURED,
                message="Google OAuth is not configured",
            ),
        )
    return cast(
        Response,
        await oauth.google.authorize_redirect(request, settings.google_redirect_uri),
    )


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=503,
            detail=structured_detail(
                code=ErrorCode.GOOGLE_OAUTH_NOT_CONFIGURED,
                message="Google OAuth is not configured",
            ),
        )

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=structured_detail(
                code=ErrorCode.GOOGLE_AUTHORIZATION_FAILED,
                message="Google authorization failed",
            ),
        ) from exc

    user_info = token.get("userinfo")
    if not isinstance(user_info, dict):
        raise HTTPException(
            status_code=400,
            detail=structured_detail(
                code=ErrorCode.GOOGLE_USER_INFO_MISSING,
                message="Google user info missing",
            ),
        )

    sub = user_info.get("sub")
    email = user_info.get("email")
    if not isinstance(sub, str) or not isinstance(email, str):
        raise HTTPException(
            status_code=400,
            detail=structured_detail(
                code=ErrorCode.GOOGLE_USER_INFO_INCOMPLETE,
                message="Google user info incomplete",
            ),
        )

    profile = GoogleProfile(
        sub=sub,
        email=email,
        email_verified=bool(user_info.get("email_verified")),
    )
    try:
        visitor_id = parse_visitor_id(request.cookies.get(settings.guest_visitor_cookie_name))
        tokens = authenticate_google_profile(db, profile, visitor_id=visitor_id)
    except AuthError as exc:
        _handle_auth_error(exc)
    user_created_param = "&user_created=1" if tokens.user_created else ""
    redirect_url = (
        f"{settings.frontend_url}/auth/google/callback"
        f"#access_token={tokens.access_token}&refresh_token={tokens.refresh_token}{user_created_param}"
    )
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post("/google", response_model=TokenResponse)
def google_id_token_login(
    body: GoogleIdTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        profile = verify_google_id_token(body.id_token)
        tokens = authenticate_google_profile(
            db,
            profile,
            visitor_id=parse_visitor_id(body.visitor_id),
        )
    except AuthError as exc:
        _handle_auth_error(exc)
    return _to_token_response(tokens)


@router.post("/telegram", response_model=TokenResponse)
def telegram_mini_app_login(
    body: TelegramAuthRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        tokens = authenticate_telegram_init_data(
            db,
            init_data=body.init_data,
            timezone=body.timezone,
        )
    except AuthError as exc:
        _handle_auth_error(exc)
    return _to_token_response(tokens)


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return _to_user_public(current_user)


@router.patch("/me", response_model=UserPublic)
def patch_me(
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserPublic:
    try:
        user = update_user_timezone(db, user_id=current_user.id, timezone=body.timezone)
    except AuthError as exc:
        _handle_auth_error(exc)
    return _to_user_public(user)
