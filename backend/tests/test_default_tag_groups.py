"""Tests for default tag group seed data."""

from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
from app.core.i18n import SUPPORTED_LOCALES


def test_default_tag_groups_have_i18n_labels() -> None:
    assert DEFAULT_TAG_GROUPS
    for group in DEFAULT_TAG_GROUPS:
        assert group.slug
        assert SUPPORTED_LOCALES.issubset(group.labels.keys())
        assert group.tags
        for tag in group.tags:
            assert tag.slug
            assert SUPPORTED_LOCALES.issubset(tag.labels.keys())
            assert tag.color.startswith("#") and len(tag.color) == 7
            assert tag.icon
