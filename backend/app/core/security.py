import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.config import settings

password_hasher = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": ACCESS_TOKEN_TYPE,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Invalid token type")
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise jwt.InvalidTokenError("Missing subject")
    return uuid.UUID(sub)


def auth_token_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(hours=settings.auth_token_expire_hours)
