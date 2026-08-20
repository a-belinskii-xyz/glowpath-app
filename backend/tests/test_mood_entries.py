import io
from datetime import date, timedelta

from app.models.goal import Goal
from app.models.tag import Tag
from app.models.user import User
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
    goal_ids: list[str] | None = None,
    source: str | None = None,
    headers: dict[str, str] | None = None,
):
    payload: dict = {
        "score": score,
        "recorded_at": recorded_at,
        "tag_ids": tag_ids or [],
        "goal_ids": goal_ids or [],
    }
    if note is not None:
        payload["note"] = note
    if source is not None:
        payload["source"] = source
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
    assert body["score_color"] == "#34d399"
    assert body["note"] is None
    assert body["tags"] == []
    assert body["goals"] == []
    assert body["attachments"] == []
    assert body["recorded_at"].endswith("+00:00") or body["recorded_at"].endswith("Z")


def test_create_mood_entry_with_notification_source(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    from app.models.mood_entry import MoodEntry

    token = register_verify_and_login(auth_client, mailer, "mood-source@example.com")
    response = _create_entry(auth_client, token, source="email:daily_mood_reminder")

    assert response.status_code == 201
    body = response.json()
    assert "source" not in body

    entry = db.scalar(select(MoodEntry).where(MoodEntry.id == body["id"]))
    assert entry is not None
    assert entry.source == "email:daily_mood_reminder"


def test_create_mood_entry_rejects_unknown_source(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-bad-source@example.com")
    response = _create_entry(auth_client, token, source="not_a_real_source")
    assert response.status_code == 422


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


def test_markdown_note_counts_plain_text_only(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-md-note@example.com")
    marked = f"**{'x' * 500}**"
    assert len(marked) > 500

    ok = _create_entry(auth_client, token, note=marked)
    assert ok.status_code == 201
    assert ok.json()["note"] == marked

    too_long = f"**{'x' * 501}**"
    rejected = _create_entry(auth_client, token, note=too_long)
    assert rejected.status_code == 422


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


def test_reorder_photo_attachments(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-reorder-photos@example.com")
    entry_id = _create_entry(auth_client, token).json()["id"]
    headers = _auth_headers(token)

    photo_ids: list[str] = []
    for index in range(3):
        response = auth_client.post(
            f"/v1/mood-entries/{entry_id}/attachments",
            headers=headers,
            data={"kind": "photo"},
            files={
                "file": (
                    f"shot-{index}.jpg",
                    io.BytesIO(f"photo-{index}".encode()),
                    "image/jpeg",
                )
            },
        )
        assert response.status_code == 201
        photo_ids.append(response.json()["id"])

    reordered_ids = list(reversed(photo_ids))
    reorder = auth_client.put(
        f"/v1/mood-entries/{entry_id}/attachments/reorder",
        headers=headers,
        json={"ordered_ids": reordered_ids},
    )
    assert reorder.status_code == 200
    body = reorder.json()
    assert [item["id"] for item in body] == reordered_ids
    assert [item["position"] for item in body] == [1, 2, 3]

    entry = auth_client.get(f"/v1/mood-entries/{entry_id}", headers=headers)
    assert entry.status_code == 200
    photos = [item for item in entry.json()["attachments"] if item["kind"] == "photo"]
    assert [item["id"] for item in photos] == reordered_ids
    assert [item["position"] for item in photos] == [1, 2, 3]


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


def test_favorite_toggle_and_list_filter(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-favorite@example.com")

    favorite = _create_entry(auth_client, token, note="keep")
    assert favorite.status_code == 201
    assert favorite.json()["is_favorite"] is False
    favorite_id = favorite.json()["id"]

    plain = _create_entry(auth_client, token, note="skip")
    assert plain.status_code == 201
    plain_id = plain.json()["id"]

    patched = auth_client.patch(
        f"/v1/mood-entries/{favorite_id}",
        json={"is_favorite": True},
        headers=_auth_headers(token),
    )
    assert patched.status_code == 200
    assert patched.json()["is_favorite"] is True

    favorites_only = auth_client.get(
        "/v1/mood-entries",
        params={"is_favorite": True},
        headers=_auth_headers(token),
    )
    assert favorites_only.status_code == 200
    favorite_ids = {item["id"] for item in favorites_only.json()["items"]}
    assert favorite_ids == {favorite_id}

    non_favorites = auth_client.get(
        "/v1/mood-entries",
        params={"is_favorite": False},
        headers=_auth_headers(token),
    )
    assert non_favorites.status_code == 200
    non_favorite_ids = {item["id"] for item in non_favorites.json()["items"]}
    assert non_favorite_ids == {plain_id}

    cleared = auth_client.patch(
        f"/v1/mood-entries/{favorite_id}",
        json={"is_favorite": False},
        headers=_auth_headers(token),
    )
    assert cleared.status_code == 200
    assert cleared.json()["is_favorite"] is False


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
    assert july_15["scores"] == [{"score": 4, "score_emoji": "🙂", "score_color": "#34d399"}]


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
    assert body["favorite_count"] == 0
    assert body["tags"] == []
    assert body["goals"] == []


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


def test_stats_includes_month_recap_icons(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    email = "mood-stats-recap@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = _auth_headers(token)
    tag_ids = _user_tag_ids(db, email)
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    goal = db.scalar(select(Goal).where(Goal.user_id == user.id).order_by(Goal.sort_order))
    assert goal is not None
    goal_id = str(goal.id)

    patched = auth_client.patch(
        f"/v1/goals/{goal_id}",
        json={"starts_on": "2026-07-01"},
        headers=headers,
    )
    assert patched.status_code == 200

    first = _create_entry(
        auth_client,
        token,
        score=5,
        recorded_at="2026-07-14T09:00:00+03:00",
        tag_ids=[tag_ids[0]],
        goal_ids=[goal_id],
    )
    assert first.status_code == 201
    favorited = auth_client.patch(
        f"/v1/mood-entries/{first.json()['id']}",
        json={"is_favorite": True},
        headers=headers,
    )
    assert favorited.status_code == 200

    second = _create_entry(
        auth_client,
        token,
        score=4,
        recorded_at="2026-07-15T10:00:00+03:00",
        tag_ids=[tag_ids[0], tag_ids[1]],
        goal_ids=[goal_id],
    )
    assert second.status_code == 201

    response = auth_client.get(
        "/v1/mood-entries/stats",
        params={
            "recorded_from": "2026-07-01T00:00:00+03:00",
            "recorded_to": "2026-08-01T00:00:00+03:00",
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["favorite_count"] == 1
    tags_by_id = {item["id"]: item for item in body["tags"]}
    assert tags_by_id[tag_ids[0]]["kind"] == "tag"
    assert tags_by_id[tag_ids[0]]["count"] == 2
    assert tags_by_id[tag_ids[1]]["count"] == 1
    assert tags_by_id[tag_ids[0]]["icon"]
    assert body["goals"][0]["id"] == goal_id
    assert body["goals"][0]["kind"] == "goal"
    assert body["goals"][0]["count"] == 2
    assert body["goals"][0]["icon"]
    weeks = {item["week"]: item for item in body["weeks"]}
    assert sorted(weeks) == [2, 3]
    assert weeks[2]["entry_count"] == 1
    assert weeks[3]["entry_count"] == 1
    assert any(score["score"] == 5 for score in weeks[2]["scores"])
    assert weeks[2]["tags"][0]["id"] == tag_ids[0]
    assert weeks[2]["goals"][0]["id"] == goal_id


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


def test_create_entry_snapshots_mood_color_and_keeps_it_after_palette_change(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-color-history@example.com")
    headers = _auth_headers(token)

    created = _create_entry(auth_client, token, score=4)
    assert created.status_code == 201
    entry_id = created.json()["id"]
    assert created.json()["score_color"] == "#34d399"

    patch_prefs = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"scores": {"4": {"color": "#ff00aa"}}},
    )
    assert patch_prefs.status_code == 200
    assert patch_prefs.json()["scores"]["4"]["color"] == "#ff00aa"

    stored = auth_client.get(f"/v1/mood-entries/{entry_id}", headers=headers)
    assert stored.status_code == 200
    assert stored.json()["score_color"] == "#34d399"

    live = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"use_historical_colors": False},
    )
    assert live.status_code == 200
    assert live.json()["use_historical_colors"] is False

    current = auth_client.get(f"/v1/mood-entries/{entry_id}", headers=headers)
    assert current.status_code == 200
    assert current.json()["score_color"] == "#ff00aa"

    calendar = auth_client.get(
        "/v1/mood-entries/calendar",
        params={
            "recorded_from": "2026-07-01T00:00:00+03:00",
            "recorded_to": "2026-08-01T00:00:00+03:00",
        },
        headers=headers,
    )
    assert calendar.status_code == 200
    day = calendar.json()["days"][0]
    assert day["scores"][0]["score_color"] == "#ff00aa"


def test_patch_score_snapshots_current_color_for_new_score(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-color-score-patch@example.com")
    headers = _auth_headers(token)

    created = _create_entry(auth_client, token, score=4)
    entry_id = created.json()["id"]
    assert created.json()["score_color"] == "#34d399"

    assert (
        auth_client.patch(
            "/v1/mood-preferences",
            headers=headers,
            json={"scores": {"5": {"color": "#abcdef"}}},
        ).status_code
        == 200
    )

    patched = auth_client.patch(
        f"/v1/mood-entries/{entry_id}",
        json={"score": 5},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["score"] == 5
    assert patched.json()["score_color"] == "#abcdef"


def test_entry_keeps_tag_color_snapshot_when_tag_color_changes(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-tag-color-history@example.com")
    headers = _auth_headers(token)
    tag_ids = _user_tag_ids(db, "mood-tag-color-history@example.com")
    tag_id = tag_ids[0]

    tags = list(db.scalars(select(Tag).where(Tag.id == tag_id)).all())
    assert tags
    original_color = tags[0].color
    group_id = tags[0].group_id

    created = _create_entry(auth_client, token, tag_ids=[tag_id])
    assert created.status_code == 201
    assert created.json()["tags"][0]["color"] == original_color
    entry_id = created.json()["id"]

    patched_tag = auth_client.patch(
        f"/v1/tag-groups/{group_id}/tags/{tag_id}",
        headers=headers,
        json={"color": "#112233"},
    )
    assert patched_tag.status_code == 200
    assert patched_tag.json()["color"] == "#112233"

    stored = auth_client.get(f"/v1/mood-entries/{entry_id}", headers=headers)
    assert stored.json()["tags"][0]["color"] == original_color

    assert (
        auth_client.patch(
            "/v1/mood-preferences",
            headers=headers,
            json={"use_historical_colors": False},
        ).status_code
        == 200
    )
    live = auth_client.get(f"/v1/mood-entries/{entry_id}", headers=headers)
    assert live.json()["tags"][0]["color"] == "#112233"


def test_insights_empty_when_too_few_days(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-insights-empty@example.com")
    _create_entry(auth_client, token, score=4, recorded_at="2026-07-10T12:00:00+03:00")

    response = auth_client.get(
        "/v1/mood-entries/insights",
        params={
            "recorded_from": "2026-06-01T00:00:00+03:00",
            "recorded_to": "2026-08-01T00:00:00+03:00",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["entry_count"] == 1
    assert body["active_days"] == 1
    assert body["items"] == []


def test_insights_weekend_pattern(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-insights-weekend@example.com")
    start = date(2026, 6, 1)  # Monday
    for offset in range(28):
        day = start + timedelta(days=offset)
        score = 5 if day.weekday() >= 5 else 3
        recorded_at = f"{day.isoformat()}T12:00:00+03:00"
        created = _create_entry(auth_client, token, score=score, recorded_at=recorded_at)
        assert created.status_code == 201

    response = auth_client.get(
        "/v1/mood-entries/insights",
        params={
            "recorded_from": "2026-06-01T00:00:00+03:00",
            "recorded_to": "2026-07-01T00:00:00+03:00",
            "limit": 4,
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["active_days"] == 28
    kinds = {item["kind"] for item in body["items"]}
    assert "weekend" in kinds
    weekend = next(item for item in body["items"] if item["kind"] == "weekend")
    assert weekend["direction"] == "higher"
    assert weekend["stats"]["delta"] is not None
    assert weekend["stats"]["delta"] > 0
    assert "weekend" in weekend["title"].lower()


def test_insights_rejects_incomplete_and_inverted_range(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-insights-range@example.com")
    incomplete = auth_client.get(
        "/v1/mood-entries/insights",
        params={"recorded_from": "2026-06-01T00:00:00+03:00"},
        headers=_auth_headers(token),
    )
    assert incomplete.status_code == 400
    assert incomplete.json()["detail"]["code"] == "recorded_range_incomplete"

    inverted = auth_client.get(
        "/v1/mood-entries/insights",
        params={
            "recorded_from": "2026-08-01T00:00:00+03:00",
            "recorded_to": "2026-07-01T00:00:00+03:00",
        },
        headers=_auth_headers(token),
    )
    assert inverted.status_code == 400
    assert inverted.json()["detail"]["code"] == "recorded_to_before_from"
