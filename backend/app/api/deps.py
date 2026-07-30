import jwt
from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import structured_detail
from app.core.i18n import normalize_locale, parse_accept_language
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_id
from app.services.email_service import EmailService, email_service
from app.services.storage import ObjectStorage, storage_service

security_scheme = HTTPBearer(auto_error=False)


def get_email_service() -> EmailService:
    return email_service


def get_storage_service() -> ObjectStorage:
    return storage_service


def get_locale(
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    locale: str | None = Query(default=None),
) -> str:
    if locale is not None:
        return normalize_locale(locale)
    return parse_accept_language(accept_language)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=structured_detail(code="not_authenticated", message="Not authenticated"),
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=structured_detail(code="invalid_token", message="Invalid token"),
        ) from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=structured_detail(code="user_not_found", message="User not found"),
        )
    return user


def get_current_verified_user(user: User = Depends(get_current_user)) -> User:
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=structured_detail(
                code="email_not_verified",
                message="Email address is not verified",
            ),
        )
    return user


def require_telegram_bot_service(
    x_telegram_bot_service_token: str | None = Header(default=None),
) -> None:
    expected = settings.telegram_bot_service_token.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=structured_detail(
                code="telegram_bot_service_token_not_configured",
                message="Telegram bot service token is not configured",
            ),
        )
    if not x_telegram_bot_service_token or x_telegram_bot_service_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=structured_detail(
                code="invalid_telegram_bot_service_token",
                message="Invalid telegram bot service token",
            ),
        )
