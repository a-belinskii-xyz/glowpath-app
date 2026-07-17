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


def test_patch_mood_preferences_rejects_upload_icon_type(auth_client: TestClient, mailer) -> None:
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
