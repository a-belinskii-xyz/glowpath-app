import uuid

from app.config import settings
from app.core.feature_flags import FeatureFlag, is_feature_enabled, stable_bucket


def test_kill_switch_disables_allowlist_and_percent(monkeypatch) -> None:
    user_id = uuid.uuid4()
    monkeypatch.setattr(settings, "feature_achievements", False)
    monkeypatch.setattr(settings, "feature_achievements_percent", 100)
    monkeypatch.setattr(settings, "feature_achievements_emails", "in@example.com")
    monkeypatch.setattr(settings, "feature_achievements_user_ids", str(user_id))

    assert (
        is_feature_enabled(
            FeatureFlag.ACHIEVEMENTS,
            user_id=user_id,
            email="in@example.com",
        )
        is False
    )


def test_allowlist_email_and_user_id(monkeypatch) -> None:
    allowlisted_id = uuid.uuid4()
    other_id = uuid.uuid4()
    monkeypatch.setattr(settings, "feature_achievements", True)
    monkeypatch.setattr(settings, "feature_achievements_percent", 0)
    monkeypatch.setattr(settings, "feature_achievements_emails", "In@example.com")
    monkeypatch.setattr(settings, "feature_achievements_user_ids", str(allowlisted_id))

    assert (
        is_feature_enabled(
            FeatureFlag.ACHIEVEMENTS,
            user_id=other_id,
            email="in@example.com",
        )
        is True
    )
    assert (
        is_feature_enabled(
            FeatureFlag.ACHIEVEMENTS,
            user_id=allowlisted_id,
            email="other@example.com",
        )
        is True
    )
    assert (
        is_feature_enabled(
            FeatureFlag.ACHIEVEMENTS,
            user_id=other_id,
            email="other@example.com",
        )
        is False
    )


def test_percent_rollout_is_stable(monkeypatch) -> None:
    user_id = uuid.uuid4()
    monkeypatch.setattr(settings, "feature_achievements", True)
    monkeypatch.setattr(settings, "feature_achievements_emails", "")
    monkeypatch.setattr(settings, "feature_achievements_user_ids", "")

    bucket = stable_bucket(FeatureFlag.ACHIEVEMENTS, user_id)
    monkeypatch.setattr(settings, "feature_achievements_percent", bucket)
    assert (
        is_feature_enabled(
            FeatureFlag.ACHIEVEMENTS,
            user_id=user_id,
            email="rollout@example.com",
        )
        is False
    )

    monkeypatch.setattr(settings, "feature_achievements_percent", bucket + 1)
    assert (
        is_feature_enabled(
            FeatureFlag.ACHIEVEMENTS,
            user_id=user_id,
            email="rollout@example.com",
        )
        is True
    )
    assert stable_bucket(FeatureFlag.ACHIEVEMENTS, user_id) == bucket
