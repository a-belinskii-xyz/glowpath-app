"""Permanent account deletion: database rows first, then stored files."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.mood_entry import MoodEntry
from app.models.mood_entry_attachment import MoodEntryAttachment
from app.models.telegram_session import TelegramSession
from app.models.user import User
from app.models.user_goal_icon import UserGoalIcon
from app.models.user_mood_icon import UserMoodIcon
from app.models.user_tag_icon import UserTagIcon
from app.services.storage import ObjectStorage, StorageError

logger = logging.getLogger(__name__)


def _user_storage_keys(db: Session, user_id: uuid.UUID) -> set[str]:
    keys = set(
        db.scalars(
            select(MoodEntryAttachment.storage_key)
            .join(MoodEntry, MoodEntry.id == MoodEntryAttachment.mood_entry_id)
            .where(MoodEntry.user_id == user_id)
        )
    )
    for model in (UserMoodIcon, UserTagIcon, UserGoalIcon):
        for key, source_key in db.execute(
            select(model.storage_key, model.source_storage_key).where(model.user_id == user_id)
        ):
            keys.add(key)
            if source_key:
                keys.add(source_key)
    return keys


def delete_account(db: Session, *, user: User, storage: ObjectStorage) -> None:
    """Delete the user and everything they own; there is no recovery window.

    Rows go through ``ON DELETE CASCADE`` (entries, tags, goals, templates, reminders,
    wallet, subscription, tokens). Icon packs the user authored stay, with the author
    set to NULL. Stored files are removed after the commit, best effort: a failed
    delete leaves an orphaned object but never a half-deleted account.
    """
    user_id = user.id
    telegram_user_id = user.telegram_user_id
    storage_keys = _user_storage_keys(db, user_id)

    if telegram_user_id is not None:
        db.execute(
            delete(TelegramSession).where(TelegramSession.telegram_user_id == telegram_user_id)
        )
    db.expunge(user)
    db.execute(delete(User).where(User.id == user_id))
    db.commit()

    failed = 0
    for key in sorted(storage_keys):
        try:
            storage.delete_object(key=key)
        except StorageError:
            failed += 1
    if failed:
        logger.warning(
            "Account %s deleted; %d of %d stored files could not be removed",
            user_id,
            failed,
            len(storage_keys),
        )
