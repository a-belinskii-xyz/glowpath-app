"""Log a mood with one tap in the Telegram chat.

A daily reminder and the bot's ``/log`` message end in a row of mood buttons. The bot
forwards a tap here and edits the message to whatever this module returns, so the
wording, the buttons and their callback data all live on the backend.

One message makes at most one entry, found again through ``MoodEntry.client_key``:
tapping another face changes the score of that entry, and "Undo" deletes it while it
is fresh and nothing was added to it in the app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.i18n import DEFAULT_LOCALE, normalize_locale
from app.core.mood_entry_source import MoodEntryAttributionKind, format_mood_entry_source
from app.core.mood_scale import MoodScore, resolve_mood_score_label
from app.core.notification_copy import NotificationText as T
from app.core.notification_copy import notification_text
from app.core.telegram_quick_log import (
    CONFIRMATION_SEPARATOR,
    UNDO_WINDOW,
    QuickTap,
    decode_quick_tap,
    question_part,
    telegram_client_key,
)
from app.models.mood_entry import MoodEntry
from app.models.user import User
from app.services.mood_entry_service import (
    create_mood_entry,
    delete_mood_entry,
    patch_mood_entry,
)
from app.services.mood_preferences_service import get_score_label_overrides
from app.services.notifications.backoff import mark_engaged
from app.services.notifications.messages import (
    STARTAPP_ONBOARDING,
    quick_log_keyboard,
    telegram_app_button,
)
from app.services.notifications.reminders import user_notification_locale
from app.services.score_faces import get_score_faces
from app.services.storage import ObjectStorage
from app.services.telegram_link_service import get_user_by_telegram_id


@dataclass(frozen=True, slots=True)
class QuickLogMessage:
    """A message with mood buttons for the bot to send."""

    text: str
    reply_markup: dict[str, Any]


@dataclass(frozen=True, slots=True)
class QuickLogReply:
    """What the bot does after a tap.

    It replaces the tapped message with ``text`` and ``reply_markup`` (``text`` None
    leaves the message alone) and shows ``toast`` over the chat, as a dialog when
    ``alert`` is set.
    """

    text: str | None
    reply_markup: dict[str, Any] | None = None
    toast: str | None = None
    alert: bool = False


@dataclass(slots=True)
class _TapContext:
    user: User
    locale: str
    question: str
    faces: dict[int, str]
    tap: QuickTap
    now: datetime
    unlocked: list[dict[str, Any]] = field(default_factory=list)


def quick_log_prompt(db: Session, *, user: User) -> QuickLogMessage:
    """The ``/log`` message: a question and the mood buttons."""
    locale = user_notification_locale(user)
    return QuickLogMessage(
        text=notification_text(T.QUICK_PROMPT, locale),
        reply_markup=quick_log_keyboard(locale=locale, faces=get_score_faces(db, user_id=user.id)),
    )


def handle_quick_tap(
    db: Session,
    *,
    telegram_user_id: int,
    chat_id: int,
    message_id: int,
    data: str,
    message_text: str | None,
    locale: str | None,
    storage: ObjectStorage,
    now: datetime | None = None,
) -> QuickLogReply:
    """Apply one tap on a mood button and say how the message should look now.

    *message_text* is the tapped message as Telegram has it; its question part is kept
    and the confirmation goes under it. *locale* is the Telegram client language, used
    only when the account is not linked.
    """
    instant = now if now is not None else datetime.now(UTC)
    user = get_user_by_telegram_id(db, telegram_user_id=telegram_user_id)
    if user is None:
        return _not_linked_reply(normalize_locale(locale) if locale else DEFAULT_LOCALE)

    user_locale = user_notification_locale(user)
    tap = decode_quick_tap(data)
    if tap is None:
        return QuickLogReply(
            text=None,
            toast=notification_text(T.QUICK_STALE_TOAST, user_locale),
            alert=True,
        )

    context = _TapContext(
        user=user,
        locale=user_locale,
        question=question_part(message_text) or notification_text(T.QUICK_PROMPT, user_locale),
        faces=get_score_faces(db, user_id=user.id),
        tap=tap,
        now=instant,
    )
    key = telegram_client_key(chat_id=chat_id, message_id=message_id)
    # Two taps on one message can arrive together; the second waits here and then
    # finds the entry the first one made.
    db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(key, 0))))
    entry = db.scalar(
        select(MoodEntry).where(MoodEntry.user_id == user.id, MoodEntry.client_key == key)
    )
    if tap.is_undo:
        return _undo(db, context, entry=entry, storage=storage)
    return _log(db, context, entry=entry, key=key)


def can_undo_quick_entry(entry: MoodEntry, *, now: datetime) -> bool:
    """Undo in the chat only removes a fresh entry that nothing was added to."""
    created = entry.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    if now - created > UNDO_WINDOW:
        return False
    has_note = bool((entry.note or "").strip())
    return not (has_note or entry.tag_links or entry.goal_links or entry.attachments)


def _log(db: Session, context: _TapContext, *, entry: MoodEntry | None, key: str) -> QuickLogReply:
    score = context.tap.score
    assert score is not None
    toast: str | None = None
    if entry is None:
        entry, context.unlocked = create_mood_entry(
            db,
            user_id=context.user.id,
            score=score,
            recorded_at=context.now,
            note=None,
            tag_ids=[],
            goal_ids=[],
            source=_entry_source(context.tap),
            locale=context.locale,
            client_key=key,
        )
        if context.tap.token:
            mark_engaged(db, token=context.tap.token, at=context.now)
        toast = notification_text(T.QUICK_SAVED_TOAST, context.locale)
    elif entry.score != score:
        entry, context.unlocked = patch_mood_entry(
            db,
            user_id=context.user.id,
            entry_id=entry.id,
            fields={"score": score},
            locale=context.locale,
        )
        toast = notification_text(T.QUICK_CHANGED_TOAST, context.locale)
    return _logged_reply(db, context, entry=entry, toast=toast)


def _undo(
    db: Session,
    context: _TapContext,
    *,
    entry: MoodEntry | None,
    storage: ObjectStorage,
) -> QuickLogReply:
    if entry is not None and not can_undo_quick_entry(entry, now=context.now):
        return _logged_reply(
            db,
            context,
            entry=entry,
            toast=notification_text(T.QUICK_UNDO_EXPIRED_TOAST, context.locale),
        )
    toast: str | None = None
    if entry is not None:
        delete_mood_entry(
            db,
            user_id=context.user.id,
            entry_id=entry.id,
            storage=storage,
            locale=context.locale,
        )
        toast = notification_text(T.QUICK_UNDONE_TOAST, context.locale)
    # With no entry (a second tap on Undo, or deleted in the app) the question comes back.
    return QuickLogReply(
        text=context.question,
        reply_markup=quick_log_keyboard(
            locale=context.locale,
            faces=context.faces,
            token=context.tap.token,
        ),
        toast=toast,
    )


def _logged_reply(
    db: Session,
    context: _TapContext,
    *,
    entry: MoodEntry,
    toast: str | None,
) -> QuickLogReply:
    label = resolve_mood_score_label(
        MoodScore(entry.score),
        context.locale,
        get_score_label_overrides(db, user_id=context.user.id),
    )
    lines = [
        notification_text(T.QUICK_LOGGED, context.locale).format(
            mood=f"{context.faces[entry.score]} {label}",
            time=_clock(entry.recorded_at, user=context.user),
        )
    ]
    lines.extend(
        notification_text(T.QUICK_ACHIEVEMENT, context.locale).format(name=item["name"])
        for item in context.unlocked
        if item.get("name")
    )
    return QuickLogReply(
        text=f"{context.question}{CONFIRMATION_SEPARATOR}" + "\n".join(lines),
        reply_markup=quick_log_keyboard(
            locale=context.locale,
            faces=context.faces,
            token=context.tap.token,
            selected=entry.score,
            entry_id=entry.id,
            can_undo=can_undo_quick_entry(entry, now=context.now),
        ),
        toast=toast,
    )


def _not_linked_reply(locale: str) -> QuickLogReply:
    button = telegram_app_button(
        startapp=STARTAPP_ONBOARDING,
        text=notification_text(T.QUICK_OPEN_BUTTON, locale),
    )
    return QuickLogReply(
        text=notification_text(T.QUICK_NOT_LINKED, locale),
        reply_markup={"inline_keyboard": [[button]]} if button is not None else None,
    )


def _entry_source(tap: QuickTap) -> str:
    """A reminder's buttons carry its token; buttons without one come from ``/log``."""
    kind = (
        MoodEntryAttributionKind.DAILY_MOOD_REMINDER if tap.token else MoodEntryAttributionKind.BOT
    )
    return format_mood_entry_source(channel="telegram", kind=kind)


def _clock(instant: datetime, *, user: User) -> str:
    try:
        zone = ZoneInfo(user.timezone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    local = instant.astimezone(zone)
    if user.time_format == "12h":
        return local.strftime("%I:%M %p").lstrip("0")
    return local.strftime("%H:%M")
