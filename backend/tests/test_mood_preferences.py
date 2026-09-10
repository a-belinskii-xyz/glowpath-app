import uuid

from app.core.mood_scale import DEFAULT_MOOD_SCORE_COLORS, MoodScore
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import register_verify_and_login


def test_get_mood_preferences_returns_defaults(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)

    response = auth_client.get(
        "/v1/mood-preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload["scores"].keys()) == {"1", "2", "3", "4", "5"}
    assert payload["scores"]["5"]["color"] == DEFAULT_MOOD_SCORE_COLORS[MoodScore.GREAT]
    assert payload["scores"]["5"]["icon_type"] == "emoji"
    assert payload["scores"]["5"]["icon"] == "😄"
    assert payload["scores"]["5"]["label"] == "great"
    assert payload["scores"]["1"]["label"] == "awful"
    assert payload["use_historical_colors"] is True
    assert payload["show_streak"] is True
    assert payload["composer_blocks"] is None


def test_patch_mood_preferences_updates_composer_blocks(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-composer-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}"}

    layout = [
        {"id": "mood", "enabled": True},
        {"id": "note", "enabled": False},
        {"id": "tags", "enabled": True},
        {"id": "goals", "enabled": False},
        {"id": "attachments", "enabled": True},
        {"id": "future_widget", "enabled": True},
    ]
    response = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"composer_blocks": layout},
    )
    assert response.status_code == 200
    saved = response.json()["composer_blocks"]
    assert saved == [
        {"id": "mood", "enabled": True},
        {"id": "note", "enabled": False},
        {"id": "tags", "enabled": True},
        {"id": "goals", "enabled": False},
        {"id": "attachments", "enabled": True},
        {"id": "future_widget", "enabled": True},
    ]

    # Partial patch of unrelated field must not snapshot/clear layout.
    color_patch = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"scores": {"1": {"color": "#112233"}}},
    )
    assert color_patch.status_code == 200
    assert color_patch.json()["composer_blocks"] == saved
    assert color_patch.json()["scores"]["1"]["color"] == "#112233"

    clear = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"composer_blocks": None},
    )
    assert clear.status_code == 200
    assert clear.json()["composer_blocks"] is None


def test_patch_mood_preferences_rejects_invalid_composer_blocks(
    auth_client: TestClient, mailer
) -> None:
    email = f"mood-prefs-composer-bad-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}"}

    empty_id = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"composer_blocks": [{"id": "  ", "enabled": True}]},
    )
    assert empty_id.status_code == 422

    too_many = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={
            "composer_blocks": [
                {"id": f"block-{index}", "enabled": True} for index in range(33)
            ]
        },
    )
    assert too_many.status_code == 422


def test_patch_mood_preferences_forces_mood_enabled(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-composer-mood-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={
            "composer_blocks": [
                {"id": "note", "enabled": True},
                {"id": "mood", "enabled": False},
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["composer_blocks"] == [
        {"id": "note", "enabled": True},
        {"id": "mood", "enabled": True},
    ]


def test_patch_mood_preferences_updates_label(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-label-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}", "Accept-Language": "ru"}

    patch_response = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"scores": {"1": {"label": "кошмарно"}}},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["scores"]["1"]["label"] == "кошмарно"
    assert patch_response.json()["scores"]["2"]["label"] == "плохо"

    get_response = auth_client.get("/v1/mood-preferences", headers=headers)
    assert get_response.json()["scores"]["1"]["label"] == "кошмарно"

    clear_response = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"scores": {"1": {"label": ""}}},
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["scores"]["1"]["label"] == "ужасно"


def test_patch_mood_preferences_rejects_long_label(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-label-long-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"scores": {"3": {"label": "x" * 41}}},
    )
    assert response.status_code == 400


def test_custom_mood_label_appears_on_entries(auth_client: TestClient, mailer) -> None:
    from tests.test_mood_entries import _create_entry

    email = f"mood-prefs-label-entry-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}", "Accept-Language": "en"}

    assert (
        auth_client.patch(
            "/v1/mood-preferences",
            headers=headers,
            json={"scores": {"4": {"label": "solid"}}},
        ).status_code
        == 200
    )

    create = _create_entry(auth_client, token, score=4, headers={"Accept-Language": "en"})
    assert create.status_code == 201
    assert create.json()["score_label"] == "solid"


def test_patch_mood_preferences_updates_color(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-patch-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}"}

    patch_response = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"scores": {"1": {"color": "#ff0000"}}},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["scores"]["1"]["color"] == "#ff0000"
    assert patch_response.json()["scores"]["2"]["color"] == DEFAULT_MOOD_SCORE_COLORS[MoodScore.BAD]

    get_response = auth_client.get("/v1/mood-preferences", headers=headers)
    assert get_response.json()["scores"]["1"]["color"] == "#ff0000"


def test_patch_mood_preferences_rejects_invalid_color(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-invalid-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"scores": {"3": {"color": "red"}}},
    )
    assert response.status_code == 400


def test_patch_mood_preferences_builtin_icon(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-builtin-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"scores": {"4": {"icon_type": "builtin", "icon": "good-sun"}}},
    )
    assert response.status_code == 200
    assert response.json()["scores"]["4"]["icon_type"] == "builtin"
    assert response.json()["scores"]["4"]["icon"] == "good-sun"


def test_patch_mood_preferences_rejects_unknown_builtin_slug(
    auth_client: TestClient,
    mailer,
) -> None:
    email = f"mood-prefs-builtin-bad-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"scores": {"2": {"icon_type": "builtin", "icon": "not-a-real-icon"}}},
    )
    assert response.status_code == 400


def test_patch_mood_preferences_emoji_icon(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-emoji-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"scores": {"3": {"icon_type": "emoji", "icon": "🫠"}}},
    )
    assert response.status_code == 200
    assert response.json()["scores"]["3"]["icon_type"] == "emoji"
    assert response.json()["scores"]["3"]["icon"] == "🫠"


def test_patch_mood_preferences_rejects_upload_without_icon_record(
    auth_client: TestClient,
    mailer,
) -> None:
    email = f"mood-prefs-upload-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "scores": {
                "4": {
                    "icon_type": "upload",
                    "icon": "00000000-0000-0000-0000-000000000001",
                }
            }
        },
    )
    assert response.status_code == 400


def test_get_mood_icon_catalog(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-catalog-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)

    response = auth_client.get(
        "/v1/mood-preferences/icon-catalog",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["items"]}
    assert "good-sun" in slugs
    assert "heart" in slugs


def test_provision_mood_preferences(db: Session) -> None:
    from app.models.user import User
    from app.services.user_provisioning import (
        count_user_mood_preferences,
        provision_mood_preferences,
    )

    user = User(email=f"mood-prefs-prov-{uuid.uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()

    provision_mood_preferences(db, user.id)
    db.flush()

    assert count_user_mood_preferences(db, user.id) == 1


def test_patch_mood_preferences_toggles_historical_colors(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-history-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"use_historical_colors": False},
    )
    assert response.status_code == 200
    assert response.json()["use_historical_colors"] is False
    assert response.json()["scores"]["4"]["color"] == DEFAULT_MOOD_SCORE_COLORS[MoodScore.GOOD]

    get_response = auth_client.get("/v1/mood-preferences", headers=headers)
    assert get_response.json()["use_historical_colors"] is False


def test_patch_mood_preferences_toggles_show_streak(auth_client: TestClient, mailer) -> None:
    email = f"mood-prefs-streak-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"show_streak": False},
    )
    assert response.status_code == 200
    assert response.json()["show_streak"] is False
    assert response.json()["use_historical_colors"] is True

    get_response = auth_client.get("/v1/mood-preferences", headers=headers)
    assert get_response.json()["show_streak"] is False
