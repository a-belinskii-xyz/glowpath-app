from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from app.config import settings
from app.core.telegram_oidc import TelegramOidcProfile, decode_id_token
from app.models.user import User
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


class _SigningKey:
    def __init__(self, key: object) -> None:
        self.key = key


class _SigningKeys:
    def __init__(self, public_key: object) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> _SigningKey:
        del token
        return _SigningKey(self._public_key)


def _rsa_keypair() -> tuple[object, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _id_token(private_key: object, *, client_id: str, telegram_user_id: int | str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": "https://oauth.telegram.org",
            "aud": client_id,
            "sub": "999000111",
            "iat": now,
            "exp": now + timedelta(minutes=10),
            "id": telegram_user_id,
            "preferred_username": "mila",
        },
        private_key,
        algorithm="RS256",
    )


def test_decode_id_token_uses_profile_id_not_sub() -> None:
    private_key, public_key = _rsa_keypair()
    token = _id_token(private_key, client_id="42", telegram_user_id=900_301)
    profile = decode_id_token(token, client_id="42", signing_keys=_SigningKeys(public_key))
    assert profile == TelegramOidcProfile(telegram_user_id=900_301, username="mila")


def test_decode_id_token_rejects_missing_profile_id() -> None:
    private_key, public_key = _rsa_keypair()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": "https://oauth.telegram.org",
            "aud": "42",
            "sub": "999000111",
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        private_key,
        algorithm="RS256",
    )
    with pytest.raises(Exception) as exc_info:
        decode_id_token(token, client_id="42", signing_keys=_SigningKeys(public_key))
    assert exc_info.value.code == "invalid_telegram_id_token"


def test_telegram_browser_login_not_configured(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_oidc_client_id", "")
    monkeypatch.setattr(settings, "telegram_oidc_client_secret", "")
    response = auth_client.get("/v1/auth/telegram/login", follow_redirects=False)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "telegram_oidc_not_configured"


def test_telegram_browser_login_creates_user(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_oidc_client_id", "42")
    monkeypatch.setattr(settings, "telegram_oidc_client_secret", "secret")
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:5173")
    monkeypatch.setattr(
        "app.services.telegram_auth_service.exchange_authorization_code",
        lambda **kwargs: "signed-id-token",
    )
    monkeypatch.setattr(
        "app.services.telegram_auth_service.decode_id_token",
        lambda token, *, client_id: TelegramOidcProfile(telegram_user_id=900_302, username="mila"),
    )

    start = auth_client.get(
        "/v1/auth/telegram/login",
        params={"timezone": "Europe/Minsk"},
        follow_redirects=False,
    )
    assert start.status_code == 302
    location = start.headers["location"]
    assert location.startswith("https://oauth.telegram.org/auth?")
    query = parse_qs(urlparse(location).query)
    assert query["client_id"] == ["42"]
    assert query["scope"] == ["openid profile"]
    assert query["code_challenge_method"] == ["S256"]

    callback = auth_client.get(
        "/v1/auth/telegram/callback",
        params={"code": "auth-code", "state": query["state"][0]},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    target = callback.headers["location"]
    assert target.startswith("http://localhost:5173/auth/telegram/callback#")
    assert "user_created=1" in target
    assert "access_token=" in target

    user = db.scalar(select(User).where(User.telegram_user_id == 900_302))
    assert user is not None
    assert user.email is None
    assert user.timezone == "Europe/Minsk"
    assert user.telegram_linked_at is not None


def test_telegram_browser_login_rejects_state_mismatch(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_oidc_client_id", "42")
    monkeypatch.setattr(settings, "telegram_oidc_client_secret", "secret")
    start = auth_client.get("/v1/auth/telegram/login", follow_redirects=False)
    assert start.status_code == 302

    callback = auth_client.get(
        "/v1/auth/telegram/callback",
        params={"code": "auth-code", "state": "not-the-state"},
        follow_redirects=False,
    )
    assert callback.status_code == 400
    assert callback.json()["detail"]["code"] == "telegram_authorization_failed"
