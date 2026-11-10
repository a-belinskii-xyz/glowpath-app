"""Rules for logging a mood with one tap in the Telegram chat.

A reminder or a ``/log`` message carries a row of mood buttons. Each button's callback
data names the action and, for a reminder, the delivery token, so the tap can count as
an answer to that reminder (see ``services/notifications/backoff.py``):

- ``q:<score>`` or ``q:<score>:<token>``: log or change the mood;
- ``q:u`` or ``q:u:<token>``: undo the entry made from this message.

The backend writes these buttons and reads them back; the bot only relays the tap.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE

CALLBACK_PREFIX = "q"
_UNDO = "u"
# Telegram limits callback_data to 64 bytes.
CALLBACK_DATA_MAX_BYTES = 64

# How long "Undo" may delete an entry made by a tap.
UNDO_WINDOW = timedelta(minutes=10)

# The confirmation goes under the question, so the question stays readable; a new tap
# or an undo cuts the message back to the part before this separator.
CONFIRMATION_SEPARATOR = "\n\n✓ "


@dataclass(frozen=True, slots=True)
class QuickTap:
    """One tap: a score to log, or ``score=None`` for undo."""

    score: int | None
    token: str | None = None

    @property
    def is_undo(self) -> bool:
        return self.score is None


def encode_quick_tap(tap: QuickTap) -> str:
    action = _UNDO if tap.score is None else str(tap.score)
    base = f"{CALLBACK_PREFIX}:{action}"
    if not tap.token:
        return base
    data = f"{base}:{tap.token}"
    # A token that does not fit is dropped: the tap still logs, it just is not tied to
    # the reminder, which backoff then credits through the entry time instead.
    return data if len(data.encode()) <= CALLBACK_DATA_MAX_BYTES else base


def decode_quick_tap(data: str) -> QuickTap | None:
    """Parse callback data written by ``encode_quick_tap``; ``None`` for anything else."""
    parts = data.split(":")
    if len(parts) not in (2, 3) or parts[0] != CALLBACK_PREFIX:
        return None
    token = parts[2] if len(parts) == 3 else None
    if token == "":
        return None
    action = parts[1]
    if action == _UNDO:
        return QuickTap(score=None, token=token)
    if not action.isdigit():
        return None
    score = int(action)
    if not MIN_MOOD_SCORE <= score <= MAX_MOOD_SCORE:
        return None
    return QuickTap(score=score, token=token)


def telegram_client_key(*, chat_id: int, message_id: int) -> str:
    """Key of the chat message an entry was made from (``MoodEntry.client_key``)."""
    return f"tg:{chat_id}:{message_id}"


def question_part(message_text: str | None) -> str:
    """The message text without the confirmation line a previous tap added."""
    if not message_text:
        return ""
    return message_text.split(CONFIRMATION_SEPARATOR, 1)[0].strip()
