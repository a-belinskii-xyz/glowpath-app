"""Telegram browser login via OpenID Connect (authorization code + PKCE).

See https://core.telegram.org/bots/telegram-login
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from app.core.error_codes import ErrorCode
from app.services.auth_service import AuthError

TELEGRAM_OIDC_ISSUER = "https://oauth.telegram.org"
TELEGRAM_OIDC_AUTH_URL = "https://oauth.telegram.org/auth"
TELEGRAM_OIDC_TOKEN_URL = "https://oauth.telegram.org/token"
TELEGRAM_OIDC_JWKS_URL = "https://oauth.telegram.org/.well-known/jwks.json"
TELEGRAM_OIDC_SCOPE = "openid profile"
_ALLOWED_ALGS = ["RS256", "ES256"]

_jwk_client: PyJWKClient | None = None


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


@dataclass(frozen=True, slots=True)
class TelegramOidcProfile:
    telegram_user_id: int
    username: str | None = None


def telegram_oidc_configured(*, client_id: str, client_secret: str) -> bool:
    return bool(client_id.strip() and client_secret.strip())


def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def generate_oidc_state() -> str:
    return secrets.token_urlsafe(32)


def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": TELEGRAM_OIDC_SCOPE,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{TELEGRAM_OIDC_AUTH_URL}?{query}"


def exchange_authorization_code(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code_verifier: str,
    timeout_seconds: float = 10.0,
) -> str:
    try:
        response = httpx.post(
            TELEGRAM_OIDC_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": code_verifier,
            },
            auth=(client_id, client_secret),
            headers={"Accept": "application/json"},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AuthError(
            "Telegram authorization failed",
            code=ErrorCode.TELEGRAM_AUTHORIZATION_FAILED,
            status_code=400,
        ) from exc

    if not isinstance(payload, dict):
        raise AuthError(
            "Telegram authorization failed",
            code=ErrorCode.TELEGRAM_AUTHORIZATION_FAILED,
            status_code=400,
        )
    id_token = payload.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise AuthError(
            "Telegram authorization failed",
            code=ErrorCode.TELEGRAM_AUTHORIZATION_FAILED,
            status_code=400,
        )
    return id_token


def decode_id_token(
    id_token: str,
    *,
    client_id: str,
    signing_keys: SigningKeyClient | None = None,
) -> TelegramOidcProfile:
    try:
        keys = signing_keys or _jwks_client()
        signing_key = keys.get_signing_key_from_jwt(id_token)
        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=_ALLOWED_ALGS,
            audience=client_id,
            issuer=TELEGRAM_OIDC_ISSUER,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthError(
            "Invalid Telegram ID token",
            code=ErrorCode.INVALID_TELEGRAM_ID_TOKEN,
            status_code=401,
        ) from exc

    if not isinstance(payload, dict):
        raise AuthError(
            "Invalid Telegram ID token",
            code=ErrorCode.INVALID_TELEGRAM_ID_TOKEN,
            status_code=401,
        )
    return TelegramOidcProfile(
        telegram_user_id=_require_telegram_user_id(payload.get("id")),
        username=_optional_str(payload.get("preferred_username")),
    )


def _require_telegram_user_id(value: object) -> int:
    if isinstance(value, bool) or value is None:
        raise AuthError(
            "Invalid Telegram ID token",
            code=ErrorCode.INVALID_TELEGRAM_ID_TOKEN,
            status_code=401,
        )
    if isinstance(value, int):
        user_id = value
    elif isinstance(value, str) and value.isdigit():
        user_id = int(value)
    else:
        raise AuthError(
            "Invalid Telegram ID token",
            code=ErrorCode.INVALID_TELEGRAM_ID_TOKEN,
            status_code=401,
        )
    if user_id <= 0:
        raise AuthError(
            "Invalid Telegram ID token",
            code=ErrorCode.INVALID_TELEGRAM_ID_TOKEN,
            status_code=401,
        )
    return user_id


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _jwks_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(TELEGRAM_OIDC_JWKS_URL, cache_keys=True)
    return _jwk_client
