import io

from app.models.tag import Tag
from app.services.storage import FakeStorage
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_entry(
    auth_client: TestClient,
    token: str,
    *,
    score: int = 4,
    recorded_at: str = "2026-07-10T12:00:00+03:00",
    note: str | None = None,
    tag_ids: list[str] | None = None,
    headers: dict[str, str] | None = None,
):
    payload: dict = {
        "score": score,
        "recorded_at": recorded_at,
        "tag_ids": tag_ids or [],
    }
    if note is not None:
        payload["note"] = note
    request_headers = _auth_headers(token)
    if headers:
        request_headers.update(headers)
    return auth_client.post("/v1/mood-entries", json=payload, headers=request_headers)


def _user_tag_ids(db: Session, email: str) -> list[str]:
    from app.models.user import User

    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    tags = list(db.scalars(select(Tag).where(Tag.user_id == user.id).limit(2)).all())
    assert len(tags) >= 2
    return [str(tag.id) for tag in tags]


def test_create_mood_entry_score_only(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-create@example.com")
    response = _create_entry(auth_client, token)

    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 4
    assert body["score_label"] == "good"
    assert body["score_emoji"] == "🙂"
    assert body["note"] is None
    assert body["tags"] == []
    assert body["attachments"] == []
    assert body["recorded_at"].endswith("+00:00") or body["recorded_at"].endswith("Z")


def test_create_with_tags_and_reject_foreign_tag(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token_a = register_verify_and_login(auth_client, mailer, "mood-tags-a@example.com")
    register_verify_and_login(auth_client, mailer, "mood-tags-b@example.com")
    tag_ids_a = _user_tag_ids(db, "mood-tags-a@example.com")
    tag_ids_b = _user_tag_ids(db, "mood-tags-b@example.com")

    ok = _create_entry(auth_client, token_a, tag_ids=tag_ids_a)
    assert ok.status_code == 201
    assert {tag["id"] for tag in ok.json()["tags"]} == set(tag_ids_a)

    rejected = _create_entry(auth_client, token_a, tag_ids=[tag_ids_b[0]])
    assert rejected.status_code == 400


def test_patch_partial_and_replace_tags(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-patch@example.com")
    tag_ids = _user_tag_ids(db, "mood-patch@example.com")
    created = _create_entry(auth_client, token, tag_ids=tag_ids)
    entry_id = created.json()["id"]

    patch_response = auth_client.patch(
        f"/v1/mood-entries/{entry_id}",
        json={"note": "updated", "tag_ids": [tag_ids[0]]},
        headers=_auth_headers(token),
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["note"] == "updated"
    assert body["score"] == 4
    assert [tag["id"] for tag in body["tags"]] == [tag_ids[0]]


def test_list_get_delete_and_isolation(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token_a = register_verify_and_login(auth_client, mailer, "mood-iso-a@example.com")
    token_b = register_verify_and_login(auth_client, mailer, "mood-iso-b@example.com")

    created = _create_entry(auth_client, token_a)
    entry_id = created.json()["id"]

    list_a = auth_client.get("/v1/mood-entries", headers=_auth_headers(token_a))
    assert list_a.status_code == 200
    assert len(list_a.json()["items"]) == 1

    list_b = auth_client.get("/v1/mood-entries", headers=_auth_headers(token_b))
    assert list_b.status_code == 200
    assert list_b.json()["items"] == []

    foreign_get = auth_client.get(
        f"/v1/mood-entries/{entry_id}",
        headers=_auth_headers(token_b),
    )
    assert foreign_get.status_code == 404

    delete_foreign = auth_client.delete(
        f"/v1/mood-entries/{entry_id}",
        headers=_auth_headers(token_b),
    )
    assert delete_foreign.status_code == 404

    delete_own = auth_client.delete(
        f"/v1/mood-entries/{entry_id}",
        headers=_auth_headers(token_a),
    )
    assert delete_own.status_code == 204

    missing = auth_client.get(
        f"/v1/mood-entries/{entry_id}",
        headers=_auth_headers(token_a),
    )
    assert missing.status_code == 404


def test_attachments_upload_limits_download_delete(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-media@example.com")
    entry_id = _create_entry(auth_client, token).json()["id"]

    photo = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "photo"},
        files={"file": ("shot.jpg", io.BytesIO(b"fake-photo"), "image/jpeg")},
    )
    assert photo.status_code == 201
    photo_body = photo.json()
    assert photo_body["kind"] == "photo"
    assert photo_body["position"] == 1
    assert "storage_key" not in photo_body
    assert len(storage._objects) == 1

    audio = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "audio"},
        files={"file": ("voice.mp3", io.BytesIO(b"fake-audio"), "audio/mpeg")},
    )
    assert audio.status_code == 201
    assert audio.json()["kind"] == "audio"
    assert audio.json()["position"] is None

    second_audio = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "audio"},
        files={"file": ("voice2.mp3", io.BytesIO(b"fake-audio-2"), "audio/mpeg")},
    )
    assert second_audio.status_code == 409

    oversized = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "photo"},
        files={
            "file": (
                "big.jpg",
                io.BytesIO(b"x" * (5 * 1024 * 1024 + 1)),
                "image/jpeg",
            )
        },
    )
    assert oversized.status_code == 400

    for index in range(4):
        response = auth_client.post(
            f"/v1/mood-entries/{entry_id}/attachments",
            headers=_auth_headers(token),
            data={"kind": "photo"},
            files={"file": (f"p{index}.jpg", io.BytesIO(b"img"), "image/jpeg")},
        )
        assert response.status_code == 201

    sixth_photo = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "photo"},
        files={"file": ("p5.jpg", io.BytesIO(b"img"), "image/jpeg")},
    )
    assert sixth_photo.status_code == 409

    attachment_id = photo_body["id"]
    download = auth_client.get(
        f"/v1/mood-entries/{entry_id}/attachments/{attachment_id}",
        headers=_auth_headers(token),
    )
    assert download.status_code == 200
    assert download.content == b"fake-photo"
    assert download.headers["content-type"].startswith("image/jpeg")

    delete = auth_client.delete(
        f"/v1/mood-entries/{entry_id}/attachments/{attachment_id}",
        headers=_auth_headers(token),
    )
    assert delete.status_code == 204
    assert all(attachment_id not in key for key in storage._objects)


def test_russian_labels_via_accept_language(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-i18n@example.com")
    tag_ids = _user_tag_ids(db, "mood-i18n@example.com")
    response = _create_entry(
        auth_client,
        token,
        score=1,
        tag_ids=[tag_ids[0]],
        headers={"Accept-Language": "ru"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["score_label"] == "ужасно"
    assert body["tags"][0]["label"]


def test_tag_groups_list_localized(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "tags-list@example.com")

    en = auth_client.get("/v1/tag-groups", headers=_auth_headers(token))
    assert en.status_code == 200
    en_items = en.json()["items"]
    assert len(en_items) >= 1
    assert en_items[0]["label"]
    assert len(en_items[0]["tags"]) >= 1

    ru = auth_client.get(
        "/v1/tag-groups",
        headers={**_auth_headers(token), "Accept-Language": "ru"},
    )
    assert ru.status_code == 200
    ru_items = ru.json()["items"]
    assert ru_items[0]["label"] != ""
    assert ru_items[0]["id"] == en_items[0]["id"]


def test_list_filter_by_recorded_range(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-filter@example.com")

    # July 2026 in Europe/Minsk (+03:00)
    in_july = _create_entry(auth_client, token, recorded_at="2026-07-15T12:00:00+03:00")
    assert in_july.status_code == 201
    in_june = _create_entry(auth_client, token, recorded_at="2026-06-30T23:59:00+03:00")
    assert in_june.status_code == 201
    on_august_boundary = _create_entry(
        auth_client,
        token,
        recorded_at="2026-08-01T00:00:00+03:00",
    )
    assert on_august_boundary.status_code == 201

    july_from = "2026-07-01T00:00:00+03:00"
    july_to = "2026-08-01T00:00:00+03:00"
    response = auth_client.get(
        "/v1/mood-entries",
        params={"recorded_from": july_from, "recorded_to": july_to},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    july_ids = {item["id"] for item in response.json()["items"]}
    assert july_ids == {in_july.json()["id"]}

    # recorded_to is exclusive: Aug 1 00:00 belongs to August, not July
    august_only = auth_client.get(
        "/v1/mood-entries",
        params={
            "recorded_from": "2026-08-01T00:00:00+03:00",
            "recorded_to": "2026-09-01T00:00:00+03:00",
        },
        headers=_auth_headers(token),
    )
    assert august_only.status_code == 200
    august_ids = {item["id"] for item in august_only.json()["items"]}
    assert august_ids == {on_august_boundary.json()["id"]}


def test_list_filter_isolated_between_users(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token_a = register_verify_and_login(auth_client, mailer, "mood-filter-a@example.com")
    token_b = register_verify_and_login(auth_client, mailer, "mood-filter-b@example.com")

    _create_entry(auth_client, token_a, recorded_at="2026-07-10T12:00:00+03:00")
    _create_entry(auth_client, token_b, recorded_at="2026-07-11T12:00:00+03:00")

    response = auth_client.get(
        "/v1/mood-entries",
        params={
            "recorded_from": "2026-07-01T00:00:00+03:00",
            "recorded_to": "2026-08-01T00:00:00+03:00",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_unauthenticated_cannot_create_entry(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/v1/mood-entries",
        json={"score": 3, "recorded_at": "2026-07-10T12:00:00+03:00", "tag_ids": []},
    )
    assert response.status_code == 401


def test_calendar_groups_by_day_and_caps_scores(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-calendar@example.com")

    # Four entries on the same local day (Europe/Minsk); newest first in response.
    _create_entry(auth_client, token, score=1, recorded_at="2026-07-14T09:00:00+03:00")
    _create_entry(auth_client, token, score=2, recorded_at="2026-07-14T12:00:00+03:00")
    _create_entry(auth_client, token, score=3, recorded_at="2026-07-14T15:00:00+03:00")
    _create_entry(auth_client, token, score=5, recorded_at="2026-07-14T18:00:00+03:00")
    _create_entry(auth_client, token, score=4, recorded_at="2026-07-15T10:00:00+03:00")
    # Outside range
    _create_entry(auth_client, token, score=1, recorded_at="2026-06-30T23:00:00+03:00")

    response = auth_client.get(
        "/v1/mood-entries/calendar",
        params={
            "recorded_from": "2026-07-01T00:00:00+03:00",
            "recorded_to": "2026-08-01T00:00:00+03:00",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    days = {day["date"]: day for day in response.json()["days"]}
    assert set(days) == {"2026-07-14", "2026-07-15"}

    july_14 = days["2026-07-14"]
    assert july_14["entry_count"] == 4
    assert [item["score"] for item in july_14["scores"]] == [5, 3, 2]
    assert [item["score_emoji"] for item in july_14["scores"]] == ["😄", "😐", "😞"]

    july_15 = days["2026-07-15"]
    assert july_15["entry_count"] == 1
    assert july_15["scores"] == [{"score": 4, "score_emoji": "🙂"}]


def test_calendar_rejects_inverted_range(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-calendar-range@example.com")
    response = auth_client.get(
        "/v1/mood-entries/calendar",
        params={
            "recorded_from": "2026-08-01T00:00:00+03:00",
            "recorded_to": "2026-07-01T00:00:00+03:00",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 400


def test_stats_counts_scores_for_range(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-stats@example.com")

    _create_entry(auth_client, token, score=1, recorded_at="2026-07-14T09:00:00+03:00")
    _create_entry(auth_client, token, score=5, recorded_at="2026-07-14T12:00:00+03:00")
    _create_entry(auth_client, token, score=5, recorded_at="2026-07-15T10:00:00+03:00")
    _create_entry(auth_client, token, score=3, recorded_at="2026-07-16T10:00:00+03:00")
    # Outside range
    _create_entry(auth_client, token, score=2, recorded_at="2026-06-30T23:00:00+03:00")

    response = auth_client.get(
        "/v1/mood-entries/stats",
        params={
            "recorded_from": "2026-07-01T00:00:00+03:00",
            "recorded_to": "2026-08-01T00:00:00+03:00",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_entries"] == 4
    by_score = {item["score"]: item for item in body["scores"]}
    assert list(by_score) == [1, 2, 3, 4, 5]
    assert by_score[1]["count"] == 1
    assert by_score[1]["score_emoji"] == "😢"
    assert by_score[1]["score_label"] == "awful"
    assert by_score[2]["count"] == 0
    assert by_score[3]["count"] == 1
    assert by_score[4]["count"] == 0
    assert by_score[5]["count"] == 2
    assert by_score[5]["score_emoji"] == "😄"
    assert body["active_days"] == 3
    assert body["month_index"] is not None
    assert body["comparison"]["verdict"] == "insufficient_data"
    assert body["comparison"]["previous_active_days"] == 1


def test_stats_compares_with_previous_month(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-stats-compare@example.com")

    # Previous month: three soft days around neutral/low.
    _create_entry(auth_client, token, score=2, recorded_at="2026-06-02T12:00:00+03:00")
    _create_entry(auth_client, token, score=2, recorded_at="2026-06-10T12:00:00+03:00")
    _create_entry(auth_client, token, score=3, recorded_at="2026-06-20T12:00:00+03:00")

    # Current month: three strong days.
    _create_entry(auth_client, token, score=5, recorded_at="2026-07-02T12:00:00+03:00")
    _create_entry(auth_client, token, score=5, recorded_at="2026-07-10T12:00:00+03:00")
    _create_entry(auth_client, token, score=4, recorded_at="2026-07-20T12:00:00+03:00")

    response = auth_client.get(
        "/v1/mood-entries/stats",
        params={
            "recorded_from": "2026-07-01T00:00:00+03:00",
            "recorded_to": "2026-08-01T00:00:00+03:00",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    comparison = body["comparison"]
    assert comparison["verdict"] in {"better", "much_better"}
    assert comparison["delta"] is not None
    assert comparison["delta"] > 0
    assert comparison["current_active_days"] == 3
    assert comparison["previous_active_days"] == 3
    assert "better" in comparison["message"].lower()


def test_stats_rejects_inverted_range(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-stats-range@example.com")
    response = auth_client.get(
        "/v1/mood-entries/stats",
        params={
            "recorded_from": "2026-08-01T00:00:00+03:00",
            "recorded_to": "2026-07-01T00:00:00+03:00",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 400
