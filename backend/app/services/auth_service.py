import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth_token_purpose import AuthTokenPurpose
from app.core.security import (
    auth_token_expires_at,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_raw_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.auth_token import AuthToken
from app.models.user import User
from app.services.email_service import EmailService
from app.services.user_provisioning import (
    provision_default_goals,
    provision_default_note_templates,
    provision_default_tags,
)


class AuthError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class EmailNotVerifiedError(AuthError):
    def __init__(self) -> None:
        super().__init__("Email address is not verified", status_code=403)


@dataclass(frozen=True, slots=True)
class GoogleProfile:
    sub: str
    email: str
    email_verified: bool


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class VerificationResendResult:
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class PasswordResetRequestResult:
    status: str
    message: str


def issue_token_pair(user_id: uuid.UUID) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(
    db: Session,
    *,
    email: str,
    password: str,
    timezone: str,
    email_service: EmailService,
) -> User:
    normalized_email = normalize_email(email)
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        raise AuthError("Email is already registered", status_code=409)

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        timezone=timezone,
    )
    db.add(user)
    db.flush()

    provision_default_tags(db, user.id)
    provision_default_note_templates(db, user.id)
    provision_default_goals(db, user.id, starts_on=_local_today(timezone))
    _create_auth_token(
        db,
        user_id=user.id,
        purpose=AuthTokenPurpose.EMAIL_VERIFY,
        email_service=email_service,
    )

    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, *, email: str, password: str) -> TokenPair:
    normalized_email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or user.password_hash is None:
        raise AuthError("Invalid email or password", status_code=401)
    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password", status_code=401)
    if user.email_verified_at is None:
        raise EmailNotVerifiedError()
    return issue_token_pair(user.id)


def refresh_access_token(db: Session, *, refresh_token: str) -> TokenPair:
    try:
        user_id = decode_refresh_token(refresh_token)
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired refresh token", status_code=401) from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise AuthError("Invalid or expired refresh token", status_code=401)
    if user.email_verified_at is None:
        raise EmailNotVerifiedError()
    return issue_token_pair(user.id)


def verify_email(db: Session, *, token: str) -> None:
    auth_token = _get_active_token(db, raw_token=token, purpose=AuthTokenPurpose.EMAIL_VERIFY)
    user = db.get(User, auth_token.user_id)
    if user is None:
        raise AuthError("Invalid verification token", status_code=400)

    user.email_verified_at = datetime.now(UTC)
    auth_token.used_at = datetime.now(UTC)
    db.commit()


def resend_verification_email(
    db: Session,
    *,
    email: str,
    email_service: EmailService,
) -> VerificationResendResult:
    normalized_email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        return VerificationResendResult(
            status="request_accepted",
            message=(
                "If an account with this email exists and is unverified, "
                "we sent a verification link."
            ),
        )
    if user.email_verified_at is not None:
        return VerificationResendResult(
            status="already_verified",
            message="Your email is already verified. You can log in.",
        )

    _invalidate_active_tokens(db, user_id=user.id, purpose=AuthTokenPurpose.EMAIL_VERIFY)
    _create_auth_token(
        db,
        user_id=user.id,
        purpose=AuthTokenPurpose.EMAIL_VERIFY,
        email_service=email_service,
    )
    db.commit()
    return VerificationResendResult(
        status="email_sent",
        message="Verification email sent. Check your inbox.",
    )


def forgot_password(
    db: Session,
    *,
    email: str,
    email_service: EmailService,
) -> PasswordResetRequestResult:
    normalized_email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or user.password_hash is None:
        return PasswordResetRequestResult(
            status="request_accepted",
            message=("If an account with this email exists, we sent a password reset link."),
        )

    _invalidate_active_tokens(db, user_id=user.id, purpose=AuthTokenPurpose.PASSWORD_RESET)
    _create_auth_token(
        db,
        user_id=user.id,
        purpose=AuthTokenPurpose.PASSWORD_RESET,
        email_service=email_service,
    )
    db.commit()
    return PasswordResetRequestResult(
        status="email_sent",
        message="Password reset email sent. Check your inbox.",
    )


def validate_password_reset_token(db: Session, *, token: str) -> None:
    _get_active_token(db, raw_token=token, purpose=AuthTokenPurpose.PASSWORD_RESET)


def reset_password(db: Session, *, token: str, new_password: str) -> None:
    auth_token = _get_active_token(db, raw_token=token, purpose=AuthTokenPurpose.PASSWORD_RESET)
    user = db.get(User, auth_token.user_id)
    if user is None:
        raise AuthError("Invalid reset token", status_code=400)

    user.password_hash = hash_password(new_password)
    auth_token.used_at = datetime.now(UTC)
    db.commit()


def authenticate_google_profile(db: Session, profile: GoogleProfile) -> TokenPair:
    if not profile.email:
        raise AuthError("Google account has no email", status_code=400)

    normalized_email = normalize_email(profile.email)
    user_by_google = db.scalar(select(User).where(User.google_sub == profile.sub))
    if user_by_google is not None:
        return issue_token_pair(user_by_google.id)

    user_by_email = db.scalar(select(User).where(User.email == normalized_email))
    if user_by_email is not None:
        if user_by_email.google_sub is not None and user_by_email.google_sub != profile.sub:
            raise AuthError("Email is linked to another Google account", status_code=409)
        user_by_email.google_sub = profile.sub
        if profile.email_verified and user_by_email.email_verified_at is None:
            user_by_email.email_verified_at = datetime.now(UTC)
        db.commit()
        return issue_token_pair(user_by_email.id)

    user = User(
        email=normalized_email,
        google_sub=profile.sub,
        email_verified_at=datetime.now(UTC) if profile.email_verified else None,
    )
    db.add(user)
    db.flush()
    provision_default_tags(db, user.id)
    provision_default_note_templates(db, user.id)
    provision_default_goals(db, user.id, starts_on=_local_today(user.timezone))
    db.commit()
    return issue_token_pair(user.id)


def verify_google_id_token(id_token: str) -> GoogleProfile:
    if not settings.google_client_id:
        raise AuthError("Google OAuth is not configured", status_code=503)

    try:
        payload = cast(
            dict[str, Any],
            google_id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
                id_token,
                google_requests.Request(),
                settings.google_client_id,
            ),
        )
    except ValueError as exc:
        raise AuthError("Invalid Google ID token", status_code=401) from exc

    sub = payload.get("sub")
    email = payload.get("email")
    if not isinstance(sub, str) or not isinstance(email, str):
        raise AuthError("Invalid Google ID token", status_code=401)

    email_verified = bool(payload.get("email_verified"))
    return GoogleProfile(sub=sub, email=email, email_verified=email_verified)


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def _local_today(timezone_name: str) -> date:
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except ZoneInfoNotFoundError:
        return datetime.now(UTC).date()


def _create_auth_token(
    db: Session,
    *,
    user_id: uuid.UUID,
    purpose: AuthTokenPurpose,
    email_service: EmailService,
) -> AuthToken:
    raw_token = generate_raw_token()
    auth_token = AuthToken(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        purpose=purpose.value,
        expires_at=auth_token_expires_at(),
    )
    db.add(auth_token)
    db.flush()

    user = db.get(User, user_id)
    if user is None:
        raise AuthError("User not found", status_code=500)

    if purpose is AuthTokenPurpose.EMAIL_VERIFY:
        email_service.send_verification_email(to=user.email, token=raw_token)
    elif purpose is AuthTokenPurpose.PASSWORD_RESET:
        email_service.send_password_reset_email(to=user.email, token=raw_token)

    return auth_token


def _get_active_token(db: Session, *, raw_token: str, purpose: AuthTokenPurpose) -> AuthToken:
    token_hash = hash_token(raw_token)
    auth_token = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.purpose == purpose.value,
            AuthToken.used_at.is_(None),
        )
    )
    if auth_token is None:
        raise AuthError("Invalid or expired token", status_code=400)
    if auth_token.expires_at < datetime.now(UTC):
        raise AuthError("Invalid or expired token", status_code=400)
    return auth_token


def _invalidate_active_tokens(
    db: Session,
    *,
    user_id: uuid.UUID,
    purpose: AuthTokenPurpose,
) -> None:
    db.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user_id,
            AuthToken.purpose == purpose.value,
            AuthToken.used_at.is_(None),
        )
        .values(used_at=datetime.now(UTC))
    )
