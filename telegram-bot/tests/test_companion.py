from bot.companion import companion_daypart_for_hour, pick_companion_variant
from bot.i18n import companion_t, t


def test_daypart_boundaries() -> None:
    assert companion_daypart_for_hour(3) == "lateNight"
    assert companion_daypart_for_hour(9) == "morning"
    assert companion_daypart_for_hour(12) == "midday"
    assert companion_daypart_for_hour(15) == "afternoon"
    assert companion_daypart_for_hour(19) == "evening"
    assert companion_daypart_for_hour(22) == "night"


def test_variant_stable() -> None:
    assert pick_companion_variant("a", 3) == pick_companion_variant("a", 3)


def test_companion_t_falls_back_to_base() -> None:
    assert t("en", "choose_score") == "How are you feeling?"
    text = companion_t("en", "choose_score", "UTC")
    assert text
    assert text != "choose_score"
    saved = companion_t("ru", "saved", "Europe/Minsk", variants=2, summary="🙂 good")
    assert "🙂 good" in saved
    assert "choose_score" not in saved
