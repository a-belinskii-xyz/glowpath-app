import csv
import io
import json
import zipfile

from app.models.tag import Tag
from app.models.user import User
from app.services.storage import FakeStorage
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _export(auth_client: TestClient, token: str, **headers: str) -> zipfile.ZipFile:
    response = auth_client.get("/v1/account/export", headers={**_auth_headers(token), **headers})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "glowpath-export-" in response.headers["content-disposition"]
    return zipfile.ZipFile(io.BytesIO(response.content))


def test_export_requires_auth(auth_client: TestClient) -> None:
    assert auth_client.get("/v1/account/export").status_code == 401


def test_export_contains_entries_csv_and_attachments(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "export@example.com")
    user = db.scalar(select(User).where(User.email == "export@example.com"))
    assert user is not None
    tag = db.scalars(select(Tag).where(Tag.user_id == user.id).limit(1)).one()

    entry = auth_client.post(
        "/v1/mood-entries",
        json={
            "score": 4,
            "recorded_at": "2026-07-10T12:00:00+03:00",
            "note": "Прогулка, кофе",
            "tag_ids": [str(tag.id)],
            "goal_ids": [],
        },
        headers=_auth_headers(token),
    )
    assert entry.status_code == 201
    entry_id = entry.json()["id"]
    photo = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "photo"},
        files={"file": ("shot.jpg", io.BytesIO(b"fake-photo"), "image/jpeg")},
    )
    assert photo.status_code == 201

    archive = _export(auth_client, token, **{"Accept-Language": "ru"})
    names = set(archive.namelist())
    assert {"diary.json", "entries.csv"} <= names

    payload = json.loads(archive.read("diary.json"))
    assert payload["format_version"] == 1
    assert payload["account"]["email"] == "export@example.com"
    assert payload["tag_groups"]
    assert len(payload["entries"]) == 1
    exported = payload["entries"][0]
    assert exported["note"] == "Прогулка, кофе"
    assert exported["tags"][0]["slug"] == tag.slug
    attachment = exported["attachments"][0]
    assert attachment["kind"] == "photo"
    assert attachment["file"] in names
    assert archive.read(attachment["file"]) == b"fake-photo"

    rows = list(csv.DictReader(io.StringIO(archive.read("entries.csv").decode("utf-8-sig"))))
    assert len(rows) == 1
    assert rows[0]["score"] == "4"
    assert rows[0]["note"] == "Прогулка, кофе"
    assert rows[0]["tags"] == tag.labels.get("ru", tag.labels.get("en"))
    assert rows[0]["photos"] == "1"


def test_export_survives_missing_attachment_object(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "export-lost@example.com")
    entry_id = auth_client.post(
        "/v1/mood-entries",
        json={"score": 3, "recorded_at": "2026-07-10T12:00:00+03:00", "tag_ids": []},
        headers=_auth_headers(token),
    ).json()["id"]
    auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "audio"},
        files={"file": ("voice.mp3", io.BytesIO(b"fake-audio"), "audio/mpeg")},
    )
    storage.clear()

    payload = json.loads(_export(auth_client, token).read("diary.json"))
    assert payload["entries"][0]["attachments"][0]["file"] is None


def test_export_is_isolated_between_users(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    owner = register_verify_and_login(auth_client, mailer, "export-owner@example.com")
    other = register_verify_and_login(auth_client, mailer, "export-other@example.com")
    auth_client.post(
        "/v1/mood-entries",
        json={"score": 5, "recorded_at": "2026-07-10T12:00:00+03:00", "note": "secret"},
        headers=_auth_headers(owner),
    )

    payload = json.loads(_export(auth_client, other).read("diary.json"))
    assert payload["account"]["email"] == "export-other@example.com"
    assert payload["entries"] == []
