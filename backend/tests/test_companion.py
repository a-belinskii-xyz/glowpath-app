from app.core.companion import (
    CompanionDaypart,
    companion_daypart_for_hour,
    daily_reminder_subject,
    pick_companion_variant,
)
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
    assert "evening" in evening.subject.lower() or "today" in evening.body.lower()
    assert "log your mood" in evening.body.lower()
