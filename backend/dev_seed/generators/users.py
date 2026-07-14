from __future__ import annotations

from datetime import UTC, datetime

from app.core.security import hash_password
from app.models.user import User
from sqlalchemy.orm import Session

from dev_seed.config import DEFAULT_PASSWORD
from dev_seed.personas import Persona
from dev_seed.rng import SeededRNG


def create_user(db: Session, *, persona: Persona, rng: SeededRNG) -> User:
    user_id = rng.uuid("user", persona.key)
    user = User(
        id=user_id,
        email=persona.email,
        password_hash=hash_password(DEFAULT_PASSWORD),
        google_sub=None,
        timezone=persona.timezone,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    return user
