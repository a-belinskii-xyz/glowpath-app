"""Shared identity helpers.

Telegram-native users have no email; web users may have no Telegram.
API access requires a verified email **or** a linked Telegram identity.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class IdentityUser(Protocol):
    @property
    def email_verified_at(self) -> datetime | None: ...

    @property
    def telegram_user_id(self) -> int | None: ...

    @property
    def password_hash(self) -> str | None: ...

    @property
    def google_sub(self) -> str | None: ...


def user_has_verified_identity(user: IdentityUser) -> bool:
    """True when the user may call verified application APIs."""
    if user.email_verified_at is not None:
        return True
    return user.telegram_user_id is not None


def telegram_is_only_auth_method(user: IdentityUser) -> bool:
    return user.password_hash is None and user.google_sub is None
