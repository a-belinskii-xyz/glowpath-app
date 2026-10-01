"""Open uploaded export ZIP parts safely and read ``diary.json`` out of them."""

from __future__ import annotations

import json
import zipfile
from typing import IO, Any

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.services.diary_archive.schema import DiaryArchive
from app.services.diary_archive.upgrades import (
    ArchiveWarning,
    UnsupportedArchiveVersion,
    upgrade,
)
from pydantic import ValidationError

DIARY_FILE = "diary.json"
# One uploaded ZIP part. The website export is a single file, so leave room for media.
MAX_PART_BYTES = 100 * 1024 * 1024
# Unpacked size of everything in one part, and of diary.json itself.
MAX_PART_UNPACKED_BYTES = 300 * 1024 * 1024
MAX_DIARY_BYTES = 50 * 1024 * 1024
# Media is stored without compression; anything packed tighter than this is a bomb.
MAX_COMPRESSION_RATIO = 100


class ArchiveError(AppError):
    pass


def _invalid(message: str) -> ArchiveError:
    return ArchiveError(message, code=ErrorCode.RESTORE_INVALID_ARCHIVE)


def _is_safe_name(name: str) -> bool:
    if not name or name.startswith(("/", "\\")) or "\\" in name or ":" in name:
        return False
    return ".." not in name.split("/")


class ArchivePart:
    """One uploaded ZIP part, checked for unsafe paths and zip bombs on open."""

    def __init__(self, handle: IO[bytes]) -> None:
        handle.seek(0, 2)
        if handle.tell() > MAX_PART_BYTES:
            raise ArchiveError(
                "Archive part is too large",
                code=ErrorCode.RESTORE_ARCHIVE_TOO_LARGE,
                status_code=413,
            )
        handle.seek(0)
        try:
            self._zip = zipfile.ZipFile(handle)
        except (zipfile.BadZipFile, OSError) as exc:
            raise _invalid("Not a ZIP archive") from exc

        self._members: dict[str, zipfile.ZipInfo] = {}
        unpacked = 0
        for info in self._zip.infolist():
            if info.is_dir():
                continue
            if not _is_safe_name(info.filename):
                raise _invalid("Archive contains an unsafe path")
            if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise _invalid("Archive is packed suspiciously tight")
            unpacked += info.file_size
            self._members[info.filename] = info
        if unpacked > MAX_PART_UNPACKED_BYTES:
            raise ArchiveError(
                "Archive part unpacks too large",
                code=ErrorCode.RESTORE_ARCHIVE_TOO_LARGE,
                status_code=413,
            )

    @property
    def names(self) -> set[str]:
        return set(self._members)

    @property
    def has_diary(self) -> bool:
        return DIARY_FILE in self._members

    def size(self, name: str) -> int:
        return self._members[name].file_size

    def read(self, name: str) -> bytes:
        try:
            return self._zip.read(self._members[name])
        except (zipfile.BadZipFile, OSError, KeyError) as exc:
            raise _invalid(f"Cannot read {name} from the archive") from exc

    def read_diary(self) -> tuple[DiaryArchive, int, list[ArchiveWarning]]:
        """Parse diary.json, upgrade it to the current format and validate it."""
        if self.size(DIARY_FILE) > MAX_DIARY_BYTES:
            raise ArchiveError(
                "diary.json is too large",
                code=ErrorCode.RESTORE_ARCHIVE_TOO_LARGE,
                status_code=413,
            )
        try:
            raw: Any = json.loads(self.read(DIARY_FILE))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _invalid("diary.json is not valid JSON") from exc
        if not isinstance(raw, dict):
            raise _invalid("diary.json is not an object")
        try:
            upgraded, version, warnings = upgrade(raw)
        except UnsupportedArchiveVersion as exc:
            raise ArchiveError(
                "This archive was made by a newer or unknown version of GlowPath",
                code=ErrorCode.RESTORE_UNSUPPORTED_VERSION,
                params={"version": str(exc.version)},
            ) from exc
        try:
            archive = DiaryArchive.model_validate(upgraded)
        except ValidationError as exc:
            raise _invalid("diary.json does not match the export format") from exc
        return archive, version, warnings

    def close(self) -> None:
        self._zip.close()
