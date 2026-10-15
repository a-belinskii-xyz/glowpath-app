"""Restoring a diary from export archives (GP-20)."""

import io
import json
import uuid
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

from app.core.error_codes import ErrorCode
from app.models.diary_restore import DiaryRestore
from app.models.goal import Goal
from app.models.mood_entry import MoodEntry
from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.models.user import User
from app.services.account_export_service import build_account_export_parts
from app.services.storage import FakeStorage
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

FIXTURES = Path(__file__).parent / "fixtures"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def _zip(files: dict[str, bytes], compression: int = zipfile.ZIP_STORED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _upload(
    client: TestClient, token: str, parts: list[bytes], *, restore_id: str | None = None
) -> Any:
    files = [
        ("files", (f"part{index}.zip", data, "application/zip"))
        for index, data in enumerate(parts, 1)
    ]
    path = (
        "/v1/account/restores" if restore_id is None else f"/v1/account/restores/{restore_id}/parts"
    )
    return client.post(path, headers=_auth(token), files=files)


def _fill_diary(client: TestClient, db: Session, token: str, email: str) -> dict[str, Any]:
    """Two entries with a tag, a quantity goal, a photo and a voice note."""
    user = _user(db, email)
    tag = db.scalars(select(Tag).where(Tag.user_id == user.id).order_by(Tag.slug).limit(1)).one()
    goal = Goal(
        user_id=user.id,
        slug="water",
        labels={"en": "Water"},
        times_per_week=7,
        tracking_kind="quantity",
        target_amount=8,
        unit="glasses",
        starts_on=date(2026, 1, 1),
        color="#60a5fa",
    )
    db.add(goal)
    db.commit()

    first = client.post(
        "/v1/mood-entries",
        headers=_auth(token),
        json={
            "score": 4,
            "recorded_at": "2026-07-10T12:00:00+03:00",
            "note": "Прогулка у реки",
            "tag_ids": [str(tag.id)],
            "goal_ids": [str(goal.id)],
            "goal_progress": [{"goal_id": str(goal.id), "amount": 5}],
        },
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/v1/mood-entries",
        headers=_auth(token),
        json={"score": 2, "recorded_at": "2026-07-11T09:00:00+03:00", "note": "Дождь"},
    )
    assert second.status_code == 201
    first_id = first.json()["id"]
    photo = client.post(
        f"/v1/mood-entries/{first_id}/attachments",
        headers=_auth(token),
        data={"kind": "photo"},
        files={"file": ("river.jpg", io.BytesIO(b"photo-bytes"), "image/jpeg")},
    )
    assert photo.status_code == 201
    audio = client.post(
        f"/v1/mood-entries/{first_id}/attachments",
        headers=_auth(token),
        data={"kind": "audio"},
        files={"file": ("voice.mp3", io.BytesIO(b"audio-bytes"), "audio/mpeg")},
    )
    assert audio.status_code == 201
    return {"tag": tag, "first_id": first_id}


def _export(client: TestClient, token: str) -> bytes:
    response = client.get("/v1/account/export", headers=_auth(token))
    assert response.status_code == 200
    return response.content


def _entries_view(client: TestClient, token: str) -> list[tuple[Any, ...]]:
    payload = json.loads(zipfile.ZipFile(io.BytesIO(_export(client, token))).read("diary.json"))
    return sorted(
        (
            entry["recorded_at"],
            entry["score"],
            entry["note"],
            entry["is_favorite"],
            tuple((tag["group"], tag["slug"]) for tag in entry["tags"]),
            tuple((goal["slug"], goal["amount"]) for goal in entry["goals"]),
            tuple(
                (item["kind"], item["mime_type"], item["size_bytes"])
                for item in entry["attachments"]
            ),
        )
        for entry in payload["entries"]
    )


def test_export_is_format_v2_with_tag_groups(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    token = register_verify_and_login(auth_client, mailer, "restore-v2@example.com")
    seeded = _fill_diary(auth_client, db, token, "restore-v2@example.com")
    payload = json.loads(
        zipfile.ZipFile(io.BytesIO(_export(auth_client, token))).read("diary.json")
    )
    assert payload["format_version"] == 2
    tagged = next(entry for entry in payload["entries"] if entry["tags"])
    assert tagged["tags"][0]["slug"] == seeded["tag"].slug
    assert tagged["tags"][0]["group"]
    assert tagged["goals"][0] == {
        "slug": "water",
        "labels": {"en": "Water"},
        "amount": 5,
        "color": "#60a5fa",
        "partial": False,
    }


def test_restore_round_trip_into_another_account(
    auth_client: TestClient, mailer: FakeEmailService, db: Session, storage: FakeStorage
) -> None:
    source = register_verify_and_login(auth_client, mailer, "restore-src@example.com")
    _fill_diary(auth_client, db, source, "restore-src@example.com")
    archive = _export(auth_client, source)

    target = register_verify_and_login(auth_client, mailer, "restore-dst@example.com")
    preview = _upload(auth_client, target, [archive])
    assert preview.status_code == 201, preview.text
    body = preview.json()
    assert body["status"] == "preview"
    assert body["format_version"] == 2
    summary = body["summary"]
    assert summary["entries_total"] == 2
    assert summary["entries_new"] == 2
    assert summary["goals_new"] == 1
    assert summary["attachments_total"] == 2
    assert summary["attachments_ready"] == 2
    assert summary["missing_parts"] == []
    assert summary["first_recorded_at"].startswith("2026-07-10")
    # Nothing is written before the user confirms.
    target_user = _user(db, "restore-dst@example.com")
    assert db.scalar(select(MoodEntry).where(MoodEntry.user_id == target_user.id)) is None

    applied = auth_client.post(f"/v1/account/restores/{body['id']}/apply", headers=_auth(target))
    assert applied.status_code == 200, applied.text
    assert applied.json()["status"] == "applied"
    assert applied.json()["summary"]["entries_new"] == 2
    assert applied.json()["summary"]["attachments_ready"] == 2

    assert _entries_view(auth_client, target) == _entries_view(auth_client, source)

    db.expire_all()
    restore = db.get(DiaryRestore, uuid.UUID(body["id"]))
    assert restore is not None
    assert restore.archive is None
    assert restore.stored_files == {}
    entries = list(db.scalars(select(MoodEntry).where(MoodEntry.user_id == target_user.id)))
    assert {entry.source for entry in entries} == {"restore"}
    assert {entry.restore_id for entry in entries} == {restore.id}
    assert all(entry.origin_id is not None for entry in entries)
    goal = db.scalar(select(Goal).where(Goal.user_id == target_user.id, Goal.slug == "water"))
    assert goal is not None and goal.restore_id == restore.id
    # Temporary uploads are gone; only the restored attachments stay in storage.
    assert not [key for key in storage._objects if key.startswith("restores/")]

    again = _upload(auth_client, target, [archive])
    assert again.json()["summary"]["entries_new"] == 0
    assert again.json()["summary"]["entries_existing"] == 2


def test_restore_into_the_same_account_skips_everything(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    token = register_verify_and_login(auth_client, mailer, "restore-same@example.com")
    _fill_diary(auth_client, db, token, "restore-same@example.com")
    preview = _upload(auth_client, token, [_export(auth_client, token)]).json()
    assert preview["summary"]["entries_new"] == 0
    assert preview["summary"]["tag_groups_new"] == 0
    assert preview["summary"]["goals_new"] == 0
    applied = auth_client.post(f"/v1/account/restores/{preview['id']}/apply", headers=_auth(token))
    assert applied.json()["summary"]["entries_new"] == 0


def test_v1_archive_upgrades_and_warns_about_ambiguous_tags(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    token = register_verify_and_login(auth_client, mailer, "restore-v1@example.com")
    diary = (FIXTURES / "diary_v1.json").read_bytes()
    photo_path = "attachments/0b1f2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d/photo.jpg"
    archive = _zip({"diary.json": diary, photo_path: b"jpeg-bytes"})

    preview = _upload(auth_client, token, [archive])
    assert preview.status_code == 201, preview.text
    body = preview.json()
    assert body["format_version"] == 1
    assert {"code": "ambiguous_tag", "slug": "v1-shared", "file": None} in body["warnings"]
    assert body["summary"]["tag_groups_new"] == 2
    assert body["summary"]["tags_new"] == 3

    applied = auth_client.post(f"/v1/account/restores/{body['id']}/apply", headers=_auth(token))
    assert applied.status_code == 200, applied.text

    user = _user(db, "restore-v1@example.com")
    entry = db.scalar(
        select(MoodEntry).where(
            MoodEntry.user_id == user.id,
            MoodEntry.origin_id == uuid.UUID("0b1f2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"),
        )
    )
    assert entry is not None
    assert entry.note == "Старая запись из v1"
    assert entry.score_color == "#84cc16"
    assert entry.is_favorite is True
    linked = {(link.tag.group.slug, link.tag.slug) for link in entry.tag_links}
    # The ambiguous tag goes to the first group that has it.
    assert linked == {("v1-life", "v1-walk"), ("v1-life", "v1-shared")}
    assert [(link.goal.slug, link.amount) for link in entry.goal_links] == [("v1-water", 6)]
    assert [item.kind.value for item in entry.attachments] == ["photo"]
    work = db.scalar(
        select(TagGroup).where(TagGroup.user_id == user.id, TagGroup.slug == "v1-work")
    )
    assert work is not None and work.restore_id is not None


def test_missing_part_can_be_added_before_applying(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    source = register_verify_and_login(auth_client, mailer, "restore-parts-src@example.com")
    _fill_diary(auth_client, db, source, "restore-parts-src@example.com")
    parts = build_account_export_parts(
        db,
        user=_user(db, "restore-parts-src@example.com"),
        storage=storage,
        locale="en",
        max_part_bytes=1,
    )
    blobs = [part.read() for part in parts]
    assert len(blobs) >= 2

    target = register_verify_and_login(auth_client, mailer, "restore-parts-dst@example.com")
    preview = _upload(auth_client, target, [blobs[0]]).json()
    assert preview["summary"]["parts_total"] == len(blobs)
    assert preview["summary"]["missing_parts"] == list(range(2, len(blobs) + 1))

    unrelated = _upload(
        auth_client, target, [_zip({"something.txt": b"x"})], restore_id=preview["id"]
    )
    assert unrelated.status_code == 400
    assert unrelated.json()["detail"]["code"] == ErrorCode.RESTORE_PART_UNKNOWN.value

    added = _upload(auth_client, target, blobs[1:], restore_id=preview["id"])
    assert added.status_code == 200, added.text
    assert added.json()["summary"]["missing_parts"] == []
    assert added.json()["summary"]["attachments_ready"] == 2

    applied = auth_client.post(f"/v1/account/restores/{preview['id']}/apply", headers=_auth(target))
    assert applied.json()["summary"]["attachments_ready"] == 2


def test_cancel_discards_uploaded_files(
    auth_client: TestClient, mailer: FakeEmailService, db: Session, storage: FakeStorage
) -> None:
    token = register_verify_and_login(auth_client, mailer, "restore-cancel@example.com")
    _fill_diary(auth_client, db, token, "restore-cancel@example.com")
    archive = _export(auth_client, token)
    other = register_verify_and_login(auth_client, mailer, "restore-cancel-2@example.com")
    preview = _upload(auth_client, other, [archive]).json()
    assert [key for key in storage._objects if key.startswith("restores/")]

    # Another user cannot touch this restore.
    foreign = auth_client.post(f"/v1/account/restores/{preview['id']}/apply", headers=_auth(token))
    assert foreign.status_code == 404

    cancelled = auth_client.post(
        f"/v1/account/restores/{preview['id']}/cancel", headers=_auth(other)
    )
    assert cancelled.json()["status"] == "cancelled"
    assert not [key for key in storage._objects if key.startswith("restores/")]
    late = auth_client.post(f"/v1/account/restores/{preview['id']}/apply", headers=_auth(other))
    assert late.status_code == 409
    assert late.json()["detail"]["code"] == ErrorCode.RESTORE_NOT_IN_PREVIEW.value


def test_new_preview_replaces_the_previous_one(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    token = register_verify_and_login(auth_client, mailer, "restore-replace@example.com")
    archive = _zip({"diary.json": (FIXTURES / "diary_v1.json").read_bytes()})
    first = _upload(auth_client, token, [archive]).json()
    second = _upload(auth_client, token, [archive]).json()
    db.expire_all()
    assert db.get(DiaryRestore, uuid.UUID(first["id"])).status == "cancelled"  # type: ignore[union-attr]
    assert db.get(DiaryRestore, uuid.UUID(second["id"])).status == "preview"  # type: ignore[union-attr]


def test_account_deletion_removes_preview_files(
    auth_client: TestClient, mailer: FakeEmailService, db: Session, storage: FakeStorage
) -> None:
    token = register_verify_and_login(auth_client, mailer, "restore-delete@example.com")
    photo_path = "attachments/0b1f2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d/photo.jpg"
    archive = _zip(
        {"diary.json": (FIXTURES / "diary_v1.json").read_bytes(), photo_path: b"jpeg-bytes"}
    )
    assert _upload(auth_client, token, [archive]).status_code == 201
    assert [key for key in storage._objects if key.startswith("restores/")]
    deleted = auth_client.request(
        "DELETE", "/v1/account", headers=_auth(token), json={"confirm": True}
    )
    assert deleted.status_code == 204
    assert not [key for key in storage._objects if key.startswith("restores/")]


def test_bad_uploads_are_rejected(auth_client: TestClient, mailer: FakeEmailService) -> None:
    token = register_verify_and_login(auth_client, mailer, "restore-bad@example.com")
    diary = json.loads((FIXTURES / "diary_v1.json").read_text())

    cases = [
        (b"not a zip", ErrorCode.RESTORE_INVALID_ARCHIVE),
        (_zip({"photo.jpg": b"x"}), ErrorCode.RESTORE_DIARY_MISSING),
        (_zip({"diary.json": b"{broken"}), ErrorCode.RESTORE_INVALID_ARCHIVE),
        (_zip({"diary.json": b"{}", "../evil.txt": b"x"}), ErrorCode.RESTORE_INVALID_ARCHIVE),
        (
            _zip({"diary.json": json.dumps({**diary, "format_version": 99}).encode()}),
            ErrorCode.RESTORE_UNSUPPORTED_VERSION,
        ),
        (
            _zip({"diary.json": json.dumps({**diary, "entries": [{"id": "nope"}]}).encode()}),
            ErrorCode.RESTORE_INVALID_ARCHIVE,
        ),
        (
            _zip({"diary.json": b"\0" * 2_000_000}, zipfile.ZIP_DEFLATED),
            ErrorCode.RESTORE_INVALID_ARCHIVE,
        ),
    ]
    for data, code in cases:
        response = _upload(auth_client, token, [data])
        assert response.status_code == 400, (code, response.text)
        assert response.json()["detail"]["code"] == code.value


def test_invalid_attachment_is_skipped_with_a_warning(
    auth_client: TestClient, mailer: FakeEmailService
) -> None:
    token = register_verify_and_login(auth_client, mailer, "restore-mime@example.com")
    diary = json.loads((FIXTURES / "diary_v1.json").read_text())
    diary["entries"][0]["attachments"][0]["mime_type"] = "application/x-msdownload"
    photo_path = diary["entries"][0]["attachments"][0]["file"]
    archive = _zip({"diary.json": json.dumps(diary).encode(), photo_path: b"MZ..."})
    body = _upload(auth_client, token, [archive]).json()
    assert {"code": "invalid_attachment", "slug": None, "file": photo_path} in body["warnings"]
    assert body["summary"]["attachments_ready"] == 0
    assert body["summary"]["missing_parts"] == []


def test_restore_requires_auth(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/v1/account/restores", files=[("files", ("a.zip", b"x", "application/zip"))]
    )
    assert response.status_code == 401
