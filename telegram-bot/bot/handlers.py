from __future__ import annotations

import logging
from typing import Any

from bot.api_client import ApiClientError, api_client
from bot.i18n import companion_t, normalize_bot_locale, t
from bot.keyboards import (
    confirm_keyboard,
    goals_keyboard,
    note_keyboard,
    score_keyboard,
    tags_keyboard,
)
from bot.telegram_api import (
    answer_callback_query,
    download_file,
    edit_message_reply_markup,
    get_file,
    send_message,
)
from bot.wizard import (
    FREQUENT_TAGS_GROUP_SLUG,
    MAX_PENDING_PHOTOS,
    SOURCE_BOT,
    SOURCE_DAILY,
    STEP_CONFIRM,
    STEP_GOALS,
    STEP_NOTE,
    STEP_SCORE,
    STEP_TAGS,
    add_pending_photo,
    advance_after_goals,
    advance_after_note,
    advance_after_score,
    advance_after_tags,
    entry_goals,
    entry_groups,
    format_summary,
    new_wizard_state,
    parse_callback,
    pending_photos,
    selected_set,
    toggle_id,
)

logger = logging.getLogger(__name__)


async def handle_update(update: dict[str, Any]) -> None:
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        await _handle_callback(callback)
        return

    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return

    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_user_id = from_user.get("id")
    if not isinstance(chat_id, int) or not isinstance(telegram_user_id, int):
        return

    locale = _locale_from_user(from_user)
    text = message.get("text")
    if isinstance(text, str):
        command, payload = _parse_command(text)
        if command == "/start":
            await _handle_start(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                locale=locale,
                payload=payload,
            )
            return
        if command == "/unlink":
            await _handle_unlink(chat_id=chat_id, telegram_user_id=telegram_user_id, locale=locale)
            return
        if command == "/help":
            await send_message(chat_id=chat_id, text=t(locale, "help"))
            return
        if command == "/log":
            await _start_wizard(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                locale=locale,
                source=SOURCE_BOT,
            )
            return
        if command == "/cancel":
            await _cancel_wizard(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                locale=locale,
            )
            return

        # Plain text during note step
        await _handle_note_text(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            locale=locale,
            text=text,
        )
        return

    photos = message.get("photo")
    if isinstance(photos, list) and photos:
        await _handle_photo(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            locale=locale,
            photos=photos,
            caption=message.get("caption"),
        )
        return

    voice = message.get("voice") or message.get("audio")
    if isinstance(voice, dict):
        await _handle_voice(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            locale=locale,
            voice=voice,
        )
        return

    document = message.get("document")
    if isinstance(document, dict) and _is_image_document(document):
        await _handle_photo(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            locale=locale,
            photos=[document],
            caption=message.get("caption"),
            mime_type=document.get("mime_type")
            if isinstance(document.get("mime_type"), str)
            else "image/jpeg",
        )


async def _handle_callback(callback: dict[str, Any]) -> None:
    callback_id = callback.get("id")
    data = callback.get("data")
    message = callback.get("message") or {}
    from_user = callback.get("from") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    telegram_user_id = from_user.get("id")
    locale = _locale_from_user(from_user)

    if not isinstance(callback_id, str):
        return
    if not isinstance(chat_id, int) or not isinstance(telegram_user_id, int):
        await answer_callback_query(callback_query_id=callback_id)
        return
    if not isinstance(data, str):
        await answer_callback_query(callback_query_id=callback_id)
        return

    action, payload = parse_callback(data)
    if not action:
        await answer_callback_query(callback_query_id=callback_id)
        return

    try:
        if action == "cancel":
            await answer_callback_query(callback_query_id=callback_id)
            await _cancel_wizard(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                locale=locale,
            )
            return

        session = await api_client.get_session(telegram_user_id=telegram_user_id)
        state = dict(session.get("state") or {})
        if not state.get("step"):
            await answer_callback_query(
                callback_query_id=callback_id,
                text=t(locale, "session_expired"),
            )
            return

        catalog = await api_client.catalog(telegram_user_id=telegram_user_id, locale=locale)
        locale = normalize_bot_locale(catalog.get("locale") or locale)

        if action == "score" and payload and state.get("step") == STEP_SCORE:
            state["score"] = int(payload)
            state = advance_after_score(state, catalog)
            await api_client.put_session(telegram_user_id=telegram_user_id, state=state)
            await answer_callback_query(callback_query_id=callback_id)
            if isinstance(message_id, int):
                await edit_message_reply_markup(chat_id=chat_id, message_id=message_id)
            await _prompt_current_step(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                locale=locale,
                state=state,
                catalog=catalog,
            )
            return

        if action == "tag" and payload and state.get("step") == STEP_TAGS:
            state = toggle_id(state, "tag_ids", payload)
            await api_client.put_session(telegram_user_id=telegram_user_id, state=state)
            await answer_callback_query(callback_query_id=callback_id)
            groups = entry_groups(catalog)
            index = int(state.get("group_index") or 0)
            if 0 <= index < len(groups) and isinstance(message_id, int):
                group = groups[index]
                await edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=tags_keyboard(
                        group.get("tags") or [],
                        selected_set(state, "tag_ids"),
                        locale=locale,
                    ),
                )
            return

        if action == "goal" and payload and state.get("step") == STEP_GOALS:
            state = toggle_id(state, "goal_ids", payload)
            await api_client.put_session(telegram_user_id=telegram_user_id, state=state)
            await answer_callback_query(callback_query_id=callback_id)
            if isinstance(message_id, int):
                await edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=goals_keyboard(
                        entry_goals(catalog),
                        selected_set(state, "goal_ids"),
                        locale=locale,
                    ),
                )
            return

        if action == "next":
            step = state.get("step")
            if step == STEP_TAGS:
                state = advance_after_tags(state, catalog)
            elif step == STEP_GOALS:
                state = advance_after_goals(state)
            elif step == STEP_NOTE:
                state = advance_after_note(state)
            else:
                await answer_callback_query(callback_query_id=callback_id)
                return
            await api_client.put_session(telegram_user_id=telegram_user_id, state=state)
            await answer_callback_query(callback_query_id=callback_id)
            if isinstance(message_id, int):
                await edit_message_reply_markup(chat_id=chat_id, message_id=message_id)
            await _prompt_current_step(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                locale=locale,
                state=state,
                catalog=catalog,
            )
            return

        if action == "skip":
            step = state.get("step")
            if step == STEP_GOALS:
                state["goal_ids"] = []
                state = advance_after_goals(state)
            elif step == STEP_NOTE:
                # Skip means "no content" — clear extras and continue.
                state["note"] = None
                state["pending_voice_file_id"] = None
                state["pending_voice_mime"] = None
                state["pending_photos"] = []
                state = advance_after_note(state)
            else:
                await answer_callback_query(callback_query_id=callback_id)
                return
            await api_client.put_session(telegram_user_id=telegram_user_id, state=state)
            await answer_callback_query(callback_query_id=callback_id)
            if isinstance(message_id, int):
                await edit_message_reply_markup(chat_id=chat_id, message_id=message_id)
            await _prompt_current_step(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                locale=locale,
                state=state,
                catalog=catalog,
            )
            return

        if action == "confirm" and state.get("step") == STEP_CONFIRM:
            await answer_callback_query(callback_query_id=callback_id)
            if isinstance(message_id, int):
                await edit_message_reply_markup(chat_id=chat_id, message_id=message_id)
            await _finalize_entry(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                locale=locale,
                state=state,
                catalog=catalog,
            )
            return

        await answer_callback_query(callback_query_id=callback_id)
    except ApiClientError as exc:
        logger.warning("callback failed: %s", exc.message)
        await answer_callback_query(
            callback_query_id=callback_id,
            text=t(locale, "error", detail=exc.message)[:200],
            show_alert=True,
        )


async def _handle_start(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str | None,
    payload: str | None,
) -> None:
    if payload == "log":
        await _start_wizard(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            locale=locale,
            source=SOURCE_DAILY,
        )
        return

    if not payload:
        try:
            me = await api_client.me(telegram_user_id=telegram_user_id)
        except ApiClientError as exc:
            logger.warning("me failed: %s", exc.message)
            await send_message(chat_id=chat_id, text=t(locale, "help"))
            return
        if me.get("linked"):
            linked_locale = normalize_bot_locale(me.get("locale") or locale)
            await send_message(chat_id=chat_id, text=t(linked_locale, "already_linked"))
            return
        await send_message(
            chat_id=chat_id,
            text=f"{t(locale, 'need_link')}\n\n{t(locale, 'help')}",
        )
        return

    try:
        me = await api_client.link(
            code=payload,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=chat_id,
            locale=locale,
        )
    except ApiClientError as exc:
        await send_message(
            chat_id=chat_id,
            text=t(locale, "link_failed", detail=exc.message),
        )
        return

    linked_locale = normalize_bot_locale(me.get("locale") or locale)
    await send_message(chat_id=chat_id, text=t(linked_locale, "linked_ok"))


async def _handle_unlink(*, chat_id: int, telegram_user_id: int, locale: str | None) -> None:
    try:
        await api_client.unlink(telegram_user_id=telegram_user_id)
    except ApiClientError as exc:
        await send_message(
            chat_id=chat_id,
            text=t(locale, "unlink_failed", detail=exc.message),
        )
        return
    await send_message(chat_id=chat_id, text=t(locale, "unlinked_ok"))


async def _start_wizard(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str | None,
    source: str,
) -> None:
    try:
        catalog = await api_client.catalog(telegram_user_id=telegram_user_id, locale=locale)
    except ApiClientError as exc:
        if exc.status_code == 404:
            await send_message(chat_id=chat_id, text=t(locale, "not_linked"))
            return
        await send_message(chat_id=chat_id, text=t(locale, "error", detail=exc.message))
        return

    locale = normalize_bot_locale(catalog.get("locale") or locale)
    state = new_wizard_state(source=source)
    try:
        await api_client.put_session(telegram_user_id=telegram_user_id, state=state)
    except ApiClientError as exc:
        await send_message(chat_id=chat_id, text=t(locale, "error", detail=exc.message))
        return

    await _prompt_current_step(
        chat_id=chat_id,
        telegram_user_id=telegram_user_id,
        locale=locale,
        state=state,
        catalog=catalog,
    )


async def _cancel_wizard(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str | None,
) -> None:
    try:
        session = await api_client.get_session(telegram_user_id=telegram_user_id)
        had_state = bool((session.get("state") or {}).get("step"))
        await api_client.delete_session(telegram_user_id=telegram_user_id)
    except ApiClientError as exc:
        if exc.status_code == 404:
            await send_message(chat_id=chat_id, text=t(locale, "not_linked"))
            return
        await send_message(chat_id=chat_id, text=t(locale, "error", detail=exc.message))
        return

    key = "cancelled" if had_state else "nothing_to_cancel"
    await send_message(chat_id=chat_id, text=t(locale, key))


async def _prompt_current_step(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str,
    state: dict[str, Any],
    catalog: dict[str, Any],
) -> None:
    del telegram_user_id  # reserved for future edit flows
    step = state.get("step")
    if step == STEP_SCORE:
        await send_message(
            chat_id=chat_id,
            text=companion_t(locale, "choose_score", _catalog_timezone(catalog)),
            reply_markup=score_keyboard(catalog.get("scores") or []),
        )
        return
    if step == STEP_TAGS:
        groups = entry_groups(catalog)
        index = int(state.get("group_index") or 0)
        if index >= len(groups):
            return
        group = groups[index]
        tag_prompt = (
            t(locale, "choose_frequent_tags")
            if group.get("slug") == FREQUENT_TAGS_GROUP_SLUG
            else t(locale, "choose_tags", group=group.get("label") or "")
        )
        await send_message(
            chat_id=chat_id,
            text=tag_prompt,
            reply_markup=tags_keyboard(
                group.get("tags") or [],
                selected_set(state, "tag_ids"),
                locale=locale,
            ),
        )
        return
    if step == STEP_GOALS:
        await send_message(
            chat_id=chat_id,
            text=t(locale, "choose_goals"),
            reply_markup=goals_keyboard(
                entry_goals(catalog),
                selected_set(state, "goal_ids"),
                locale=locale,
            ),
        )
        return
    if step == STEP_NOTE:
        lead = companion_t(
            locale,
            "note_lead",
            _catalog_timezone(catalog),
            variants=2,
        )
        await send_message(
            chat_id=chat_id,
            text=f"{lead}\n\n{t(locale, 'note_prompt')}",
            reply_markup=note_keyboard(locale=locale),
        )
        return
    if step == STEP_CONFIRM:
        summary = format_summary(state, catalog)
        await send_message(
            chat_id=chat_id,
            text=t(locale, "confirm", summary=summary),
            reply_markup=confirm_keyboard(locale=locale),
        )


async def _handle_note_text(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str | None,
    text: str,
) -> None:
    try:
        session = await api_client.get_session(telegram_user_id=telegram_user_id)
    except ApiClientError:
        return
    state = dict(session.get("state") or {})
    if state.get("step") != STEP_NOTE:
        return

    try:
        catalog = await api_client.catalog(telegram_user_id=telegram_user_id, locale=locale)
    except ApiClientError as exc:
        await send_message(chat_id=chat_id, text=t(locale, "error", detail=exc.message))
        return

    locale = normalize_bot_locale(catalog.get("locale") or locale)
    state["note"] = text.strip() or None
    await api_client.put_session(telegram_user_id=telegram_user_id, state=state)
    await _ack_note_content(
        chat_id=chat_id,
        locale=locale,
        state=state,
        ack_key="note_saved_step",
    )


async def _handle_voice(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str | None,
    voice: dict[str, Any],
) -> None:
    try:
        session = await api_client.get_session(telegram_user_id=telegram_user_id)
    except ApiClientError:
        return
    state = dict(session.get("state") or {})
    if state.get("step") != STEP_NOTE:
        return

    file_id = voice.get("file_id")
    if not isinstance(file_id, str):
        return
    mime = voice.get("mime_type")
    if not isinstance(mime, str) or not mime:
        mime = "audio/ogg"

    try:
        catalog = await api_client.catalog(telegram_user_id=telegram_user_id, locale=locale)
    except ApiClientError as exc:
        await send_message(chat_id=chat_id, text=t(locale, "error", detail=exc.message))
        return

    locale = normalize_bot_locale(catalog.get("locale") or locale)
    state["pending_voice_file_id"] = file_id
    state["pending_voice_mime"] = mime
    await api_client.put_session(telegram_user_id=telegram_user_id, state=state)
    await _ack_note_content(
        chat_id=chat_id,
        locale=locale,
        state=state,
        ack_key="voice_attached",
    )


async def _handle_photo(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str | None,
    photos: list[Any],
    caption: Any = None,
    mime_type: str = "image/jpeg",
) -> None:
    try:
        session = await api_client.get_session(telegram_user_id=telegram_user_id)
    except ApiClientError:
        return
    state = dict(session.get("state") or {})
    if state.get("step") != STEP_NOTE:
        return

    largest = photos[-1] if photos else None
    if not isinstance(largest, dict):
        return
    file_id = largest.get("file_id")
    if not isinstance(file_id, str):
        return

    try:
        catalog = await api_client.catalog(telegram_user_id=telegram_user_id, locale=locale)
    except ApiClientError as exc:
        await send_message(chat_id=chat_id, text=t(locale, "error", detail=exc.message))
        return

    locale = normalize_bot_locale(catalog.get("locale") or locale)
    state, error_key = add_pending_photo(state, file_id=file_id, mime_type=mime_type)
    if error_key:
        await send_message(
            chat_id=chat_id,
            text=t(locale, error_key, max=MAX_PENDING_PHOTOS),
            reply_markup=note_keyboard(locale=locale),
        )
        return

    if isinstance(caption, str) and caption.strip():
        existing = state.get("note")
        if isinstance(existing, str) and existing.strip():
            state["note"] = f"{existing.strip()}\n{caption.strip()}"
        else:
            state["note"] = caption.strip()

    await api_client.put_session(telegram_user_id=telegram_user_id, state=state)
    count = len(pending_photos(state))
    await _ack_note_content(
        chat_id=chat_id,
        locale=locale,
        state=state,
        ack_key="photo_attached",
        ack_kwargs={"count": count, "max": MAX_PENDING_PHOTOS},
    )


async def _ack_note_content(
    *,
    chat_id: int,
    locale: str,
    state: dict[str, Any],
    ack_key: str,
    ack_kwargs: dict[str, Any] | None = None,
) -> None:
    await send_message(chat_id=chat_id, text=t(locale, ack_key, **(ack_kwargs or {})))
    await send_message(
        chat_id=chat_id,
        text=t(locale, "note_status", parts=_note_parts_label(locale, state)),
        reply_markup=note_keyboard(locale=locale),
    )


def _note_parts_label(locale: str, state: dict[str, Any]) -> str:
    parts: list[str] = []
    note = state.get("note")
    if isinstance(note, str) and note.strip():
        parts.append(t(locale, "part_note"))
    if state.get("pending_voice_file_id"):
        parts.append(t(locale, "part_voice"))
    photos = pending_photos(state)
    if photos:
        parts.append(t(locale, "part_photos", count=len(photos)))
    return ", ".join(parts) if parts else "—"


async def _finalize_entry(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str,
    state: dict[str, Any],
    catalog: dict[str, Any],
) -> None:
    score = state.get("score")
    if not isinstance(score, int):
        await send_message(chat_id=chat_id, text=t(locale, "session_expired"))
        return

    try:
        entry = await api_client.create_entry(
            telegram_user_id=telegram_user_id,
            score=score,
            tag_ids=list(selected_set(state, "tag_ids")),
            goal_ids=list(selected_set(state, "goal_ids")),
            note=state.get("note") if isinstance(state.get("note"), str) else None,
            source=state.get("source") if isinstance(state.get("source"), str) else SOURCE_BOT,
        )
    except ApiClientError as exc:
        await send_message(chat_id=chat_id, text=t(locale, "error", detail=exc.message))
        return

    entry_id = str(entry["id"])
    voice_file_id = state.get("pending_voice_file_id")
    if isinstance(voice_file_id, str) and voice_file_id:
        try:
            await _upload_pending_file(
                telegram_user_id=telegram_user_id,
                entry_id=entry_id,
                file_id=voice_file_id,
                kind="audio",
                filename="voice.ogg",
                mime_type=str(state.get("pending_voice_mime") or "audio/ogg"),
            )
        except Exception as exc:
            logger.exception("voice upload failed")
            await send_message(
                chat_id=chat_id,
                text=t(locale, "error", detail=str(exc)),
            )

    for index, photo in enumerate(pending_photos(state), start=1):
        try:
            mime = str(photo.get("mime_type") or "image/jpeg")
            ext = "jpg" if "jpeg" in mime or mime == "image/jpg" else mime.split("/")[-1]
            await _upload_pending_file(
                telegram_user_id=telegram_user_id,
                entry_id=entry_id,
                file_id=str(photo["file_id"]),
                kind="photo",
                filename=f"photo-{index}.{ext}",
                mime_type=mime,
            )
        except Exception as exc:
            logger.exception("photo upload failed")
            await send_message(
                chat_id=chat_id,
                text=t(locale, "error", detail=str(exc)),
            )

    try:
        await api_client.delete_session(telegram_user_id=telegram_user_id)
    except ApiClientError:
        logger.warning("failed to clear session after save")

    summary = format_summary(state, catalog)
    await send_message(
        chat_id=chat_id,
        text=companion_t(
            locale,
            "saved",
            _catalog_timezone(catalog),
            variants=2,
            summary=summary,
        ),
    )


async def _upload_pending_file(
    *,
    telegram_user_id: int,
    entry_id: str,
    file_id: str,
    kind: str,
    filename: str,
    mime_type: str,
) -> None:
    meta = await get_file(file_id)
    file_path = meta.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        raise RuntimeError("Telegram file path missing")
    data = await download_file(file_path)
    await api_client.upload_attachment(
        telegram_user_id=telegram_user_id,
        entry_id=entry_id,
        kind=kind,
        filename=filename,
        content_type=mime_type or "application/octet-stream",
        data=data,
    )


def _is_image_document(document: dict[str, Any]) -> bool:
    mime = document.get("mime_type")
    if isinstance(mime, str) and mime.startswith("image/"):
        return True
    name = document.get("file_name")
    if isinstance(name, str):
        lower = name.lower()
        return lower.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))
    return False


def _locale_from_user(from_user: dict[str, Any]) -> str | None:
    locale = from_user.get("language_code")
    return locale if isinstance(locale, str) else None


def _catalog_timezone(catalog: dict[str, Any]) -> str | None:
    value = catalog.get("timezone")
    return value if isinstance(value, str) and value else None


def _parse_command(text: str) -> tuple[str | None, str | None]:
    parts = text.strip().split(maxsplit=1)
    if not parts:
        return None, None
    command = parts[0].split("@", 1)[0].lower()
    if not command.startswith("/"):
        return None, None
    payload = parts[1].strip() if len(parts) > 1 else None
    return command, payload or None
