"""Bring an older ``diary.json`` up to ``CURRENT_VERSION``, one version at a time.

Each step takes the raw dict of version N and returns version N + 1. Steps are
never edited once released: a newer format gets a new step instead.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services.diary_archive.schema import CURRENT_VERSION

ArchiveWarning = dict[str, Any]
Upgrade = Callable[[dict[str, Any], list[ArchiveWarning]], dict[str, Any]]


class UnsupportedArchiveVersion(Exception):
    def __init__(self, version: object) -> None:
        super().__init__(f"Unsupported diary archive version: {version!r}")
        self.version = version


def upgrade_v1_to_v2(raw: dict[str, Any], warnings: list[ArchiveWarning]) -> dict[str, Any]:
    """v1 tags in entries carry no group; v2 names it because tag slugs repeat across groups."""
    groups_by_tag: dict[str, list[str]] = {}
    for group in raw.get("tag_groups") or []:
        for tag in group.get("tags") or []:
            groups_by_tag.setdefault(str(tag.get("slug")), []).append(str(group.get("slug")))

    ambiguous: set[str] = set()
    unknown: set[str] = set()
    for entry in raw.get("entries") or []:
        tags = []
        for tag in entry.get("tags") or []:
            slug = str(tag.get("slug"))
            groups = groups_by_tag.get(slug)
            if not groups:
                unknown.add(slug)
                continue
            if len(groups) > 1:
                ambiguous.add(slug)
            tags.append({**tag, "group": groups[0]})
        entry["tags"] = tags

    warnings.extend({"code": "ambiguous_tag", "slug": slug} for slug in sorted(ambiguous))
    warnings.extend({"code": "unknown_tag", "slug": slug} for slug in sorted(unknown))
    return {**raw, "format_version": 2}


UPGRADES: dict[int, Upgrade] = {
    1: upgrade_v1_to_v2,
}


def upgrade(raw: dict[str, Any]) -> tuple[dict[str, Any], int, list[ArchiveWarning]]:
    """Return the archive at ``CURRENT_VERSION``, its original version and any warnings."""
    version = raw.get("format_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise UnsupportedArchiveVersion(version)
    if version > CURRENT_VERSION:
        raise UnsupportedArchiveVersion(version)
    original = version
    warnings: list[ArchiveWarning] = []
    while version < CURRENT_VERSION:
        raw = UPGRADES[version](raw, warnings)
        version += 1
    return raw, original, warnings
