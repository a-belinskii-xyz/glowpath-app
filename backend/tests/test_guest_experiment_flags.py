import uuid

import pytest

from app.config import settings
from app.core.feature_flags import FeatureFlag, is_feature_enabled_for_visitor, stable_bucket


def test_guest_local_diary_kill_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    visitor_id = uuid.uuid4()
    monkeypatch.setattr(settings, "feature_guest_local_diary", False)
    monkeypatch.setattr(settings, "feature_guest_local_diary_percent", 100)
    monkeypatch.setattr(settings, "feature_guest_local_diary_visitor_ids", str(visitor_id))
    assert is_feature_enabled_for_visitor(FeatureFlag.GUEST_LOCAL_DIARY, visitor_id) is False


def test_guest_local_diary_allowlist_visitor(monkeypatch: pytest.MonkeyPatch) -> None:
    allowlisted = uuid.uuid4()
    other = uuid.uuid4()
    monkeypatch.setattr(settings, "feature_guest_local_diary", True)
    monkeypatch.setattr(settings, "feature_guest_local_diary_percent", 0)
    monkeypatch.setattr(settings, "feature_guest_local_diary_visitor_ids", str(allowlisted))
    assert is_feature_enabled_for_visitor(FeatureFlag.GUEST_LOCAL_DIARY, allowlisted) is True
    assert is_feature_enabled_for_visitor(FeatureFlag.GUEST_LOCAL_DIARY, other) is False


def test_guest_local_diary_percent_is_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    visitor_id = uuid.uuid4()
    monkeypatch.setattr(settings, "feature_guest_local_diary", True)
    monkeypatch.setattr(settings, "feature_guest_local_diary_visitor_ids", "")
    bucket = stable_bucket(FeatureFlag.GUEST_LOCAL_DIARY, visitor_id)
    monkeypatch.setattr(settings, "feature_guest_local_diary_percent", bucket)
    assert is_feature_enabled_for_visitor(FeatureFlag.GUEST_LOCAL_DIARY, visitor_id) is False
    monkeypatch.setattr(settings, "feature_guest_local_diary_percent", bucket + 1)
    assert is_feature_enabled_for_visitor(FeatureFlag.GUEST_LOCAL_DIARY, visitor_id) is True
