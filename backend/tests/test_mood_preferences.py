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
