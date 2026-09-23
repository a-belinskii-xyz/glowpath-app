from datetime import UTC, datetime
from types import SimpleNamespace

from app.core.identity import telegram_is_only_auth_method, user_has_verified_identity


def test_telegram_only_until_verified_email_password() -> None:
    native = SimpleNamespace(
        email_verified_at=None,
        telegram_user_id=1,
        password_hash=None,
        google_sub=None,
    )
    assert telegram_is_only_auth_method(native) is True
    assert user_has_verified_identity(native) is True

    pending = SimpleNamespace(
        email_verified_at=None,
        telegram_user_id=1,
        password_hash="hash",
        google_sub=None,
    )
    assert telegram_is_only_auth_method(pending) is True

    ready = SimpleNamespace(
        email_verified_at=datetime.now(UTC),
        telegram_user_id=1,
        password_hash="hash",
        google_sub=None,
    )
    assert telegram_is_only_auth_method(ready) is False


def test_google_account_can_unlink_telegram() -> None:
    user = SimpleNamespace(
        email_verified_at=datetime.now(UTC),
        telegram_user_id=1,
        password_hash=None,
        google_sub="sub-1",
    )
    assert telegram_is_only_auth_method(user) is False
