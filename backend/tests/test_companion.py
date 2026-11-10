from app.core.companion import (
    _DAILY_REMINDER_INTRO,
    _DAILY_REMINDER_INTRO_NAMED,
    _DAILY_REMINDER_QUESTION,
    _DAILY_REMINDER_QUESTION_NAMED,
    CompanionDaypart,
    companion_daypart_for_hour,
    daily_reminder_intro,
    daily_reminder_question,
    daily_reminder_subject,
    pick_companion_variant,
)
from app.core.notification_copy import NotificationText, notification_text
from app.services.notifications.base import NotificationChannel
from app.services.notifications.messages import daily_mood_reminder_message


def test_companion_daypart_boundaries() -> None:
    assert companion_daypart_for_hour(0) is CompanionDaypart.LATE_NIGHT
    assert companion_daypart_for_hour(4) is CompanionDaypart.LATE_NIGHT
    assert companion_daypart_for_hour(5) is CompanionDaypart.MORNING
    assert companion_daypart_for_hour(10) is CompanionDaypart.MORNING
    assert companion_daypart_for_hour(11) is CompanionDaypart.MIDDAY
    assert companion_daypart_for_hour(13) is CompanionDaypart.MIDDAY
    assert companion_daypart_for_hour(14) is CompanionDaypart.AFTERNOON
    assert companion_daypart_for_hour(16) is CompanionDaypart.AFTERNOON
    assert companion_daypart_for_hour(17) is CompanionDaypart.EVENING
    assert companion_daypart_for_hour(20) is CompanionDaypart.EVENING
    assert companion_daypart_for_hour(21) is CompanionDaypart.NIGHT
    assert companion_daypart_for_hour(23) is CompanionDaypart.NIGHT


def test_companion_variant_is_stable() -> None:
    assert pick_companion_variant("2026-08-19:greeting:evening", 3) == pick_companion_variant(
        "2026-08-19:greeting:evening", 3
    )
    assert pick_companion_variant("seed", 1) == 0


def test_daily_reminder_copy_changes_with_hour() -> None:
    morning = daily_reminder_subject(hour=8, locale="en")
    evening = daily_reminder_subject(hour=20, locale="en")
    night = daily_reminder_subject(hour=2, locale="ru")
    assert "morning" in morning.lower()
    assert "evening" in evening.lower()
    assert morning != evening
    assert "настроение" in night.lower()


def test_daily_mood_reminder_uses_local_hour() -> None:
    morning = daily_mood_reminder_message(channel=NotificationChannel.EMAIL, hour=8)
    evening = daily_mood_reminder_message(channel=NotificationChannel.TELEGRAM, hour=20)
    assert "morning" in morning.subject.lower()
    assert "log your mood" in morning.body.lower()
    assert evening.html_body is None
    assert "evening" in evening.subject.lower()
    assert evening.body == daily_reminder_question(hour=20, locale="en")


def test_daily_reminder_intro_is_stable_per_seed_and_varies_across_days() -> None:
    first = daily_reminder_intro(hour=20, locale="ru", seed="user:2026-10-01")
    assert first == daily_reminder_intro(hour=20, locale="ru", seed="user:2026-10-01")
    seen = {
        daily_reminder_intro(hour=20, locale="en", seed=f"user:2026-10-{day:02d}")
        for day in range(1, 29)
    }
    assert len(seen) > 1


def test_every_companion_and_notification_phrase_has_ru_and_en() -> None:
    for hour in range(24):
        for locale in ("en", "ru"):
            assert daily_reminder_subject(hour=hour, locale=locale)
    for phrases in _DAILY_REMINDER_INTRO.values():
        for variants in phrases.values():
            for labels in variants:
                assert set(labels) == {"en", "ru"}
    for key in NotificationText:
        en = notification_text(key, "en")
        ru = notification_text(key, "ru")
        assert en and ru and en != ru


def test_named_reminder_intro_appears_only_with_a_name() -> None:
    plain = {
        daily_reminder_intro(hour=8, locale="ru", seed=f"user:2026-10-{day:02d}")
        for day in range(1, 29)
    }
    named = {
        daily_reminder_intro(hour=8, locale="ru", seed=f"user:2026-10-{day:02d}", name="Аня")
        for day in range(1, 29)
    }
    assert not any("Аня" in phrase or "{name}" in phrase for phrase in plain)
    assert "Доброе утро, Аня. Как ты?" in named
    assert not any("{name}" in phrase for phrase in named)
    for labels in _DAILY_REMINDER_INTRO_NAMED.values():
        assert set(labels) == {"en", "ru"}
        assert all("{name}" in text for text in labels.values())


def test_email_greeting_uses_the_name() -> None:
    message = daily_mood_reminder_message(
        channel=NotificationChannel.EMAIL, hour=8, locale="ru", display_name="Аня <3"
    )
    assert message.body.startswith("Привет, Аня <3,")
    assert message.html_body is not None
    assert "<p>Привет, Аня &lt;3,</p>" in message.html_body


def test_reminder_questions_cover_every_daypart_in_both_languages() -> None:
    for phrases in _DAILY_REMINDER_QUESTION.values():
        assert set(phrases) == set(CompanionDaypart)
        for variants in phrases.values():
            for labels in variants:
                assert set(labels) == {"en", "ru"}
                assert all(text.endswith("?") for text in labels.values())
    assert set(_DAILY_REMINDER_QUESTION_NAMED) == set(CompanionDaypart)
    for labels in _DAILY_REMINDER_QUESTION_NAMED.values():
        assert set(labels) == {"en", "ru"}
        assert all("{name}" in text and text.endswith("?") for text in labels.values())


def test_reminder_questions_do_not_ask_for_a_note() -> None:
    """The buttons answer the question, so it must not push toward writing."""
    texts = [
        text
        for phrases in _DAILY_REMINDER_QUESTION.values()
        for variants in phrases.values()
        for labels in variants
        for text in labels.values()
    ] + [text for labels in _DAILY_REMINDER_QUESTION_NAMED.values() for text in labels.values()]
    for text in texts:
        lowered = text.lower()
        for word in ("note", "word", "line", "заметк", "слов", "строчк", "запиш"):
            assert word not in lowered, text


def test_reminder_question_is_stable_per_seed_and_uses_the_name_only_sometimes() -> None:
    first = daily_reminder_question(hour=8, locale="ru", seed="user:2026-10-01")
    assert first == daily_reminder_question(hour=8, locale="ru", seed="user:2026-10-01")
    named = {
        daily_reminder_question(hour=8, locale="ru", seed=f"user:2026-10-{day:02d}", name="Аня")
        for day in range(1, 29)
    }
    assert "Доброе утро, Аня. Как ты?" in named
    assert any("Аня" not in phrase for phrase in named)
    assert not any("{name}" in phrase for phrase in named)
