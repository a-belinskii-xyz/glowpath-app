from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, extract_token_from_email, register_verify_and_login


def _register_and_get_verify_token(
    auth_client: TestClient,
    mailer: FakeEmailService,
    email: str,
) -> str:
    response = auth_client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123", "password_confirm": "password123"},
    )
    assert response.status_code == 201
    return extract_token_from_email(mailer.outbox[-1].body)


def test_login_blocked_before_email_verification(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    email = "unverified@example.com"
    _register_and_get_verify_token(auth_client, mailer, email)

    response = auth_client.post(
        "/v1/auth/login",
        json={"email": email, "password": "password123", "password_confirm": "password123"},
    )
    assert response.status_code == 403


def test_verify_then_login_and_me(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    email = "verified@example.com"
    token = _register_and_get_verify_token(auth_client, mailer, email)

    verify_response = auth_client.get(f"/v1/auth/verify-email?token={token}")
    assert verify_response.status_code == 200
    assert verify_response.json()["message"] == "Email verified successfully"

    login_response = auth_client.post(
        "/v1/auth/login",
        json={"email": email, "password": "password123", "password_confirm": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    me_response = auth_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    body = me_response.json()
    assert body["email"] == email
    assert body["email_verified"] is True


def test_refresh_token_returns_new_access_token(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    email = "refresh@example.com"
    token = _register_and_get_verify_token(auth_client, mailer, email)
    auth_client.get(f"/v1/auth/verify-email?token={token}")

    login_response = auth_client.post(
        "/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert "refresh_token" in login_body

    refresh_response = auth_client.post(
        "/v1/auth/refresh",
        json={"refresh_token": login_body["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refresh_body = refresh_response.json()
    assert refresh_body["access_token"] != login_body["access_token"]
    assert "refresh_token" in refresh_body

    me_response = auth_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_body['access_token']}"},
    )
    assert me_response.status_code == 200


def test_register_rejects_mismatched_passwords(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/v1/auth/register",
        json={
            "email": "mismatch@example.com",
            "password": "password123",
            "password_confirm": "password456",
        },
    )
    assert response.status_code == 422


def test_resend_verification_sends_email(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    email = "resend@example.com"
    _register_and_get_verify_token(auth_client, mailer, email)
    mailer.clear_outbox()

    response = auth_client.post("/v1/auth/resend-verification", json={"email": email})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "email_sent"
    assert "Verification email sent" in body["message"]
    assert len(mailer.outbox) == 1


def test_resend_verification_already_verified(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    email = "verified-resend@example.com"
    token = _register_and_get_verify_token(auth_client, mailer, email)
    auth_client.get(f"/v1/auth/verify-email?token={token}")
    mailer.clear_outbox()

    response = auth_client.post("/v1/auth/resend-verification", json={"email": email})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "already_verified"
    assert "already verified" in body["message"].lower()
    assert len(mailer.outbox) == 0


def test_resend_verification_unknown_email_returns_request_accepted(
    auth_client: TestClient,
) -> None:
    response = auth_client.post(
        "/v1/auth/resend-verification",
        json={"email": "missing@example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "request_accepted"
    assert "verification link" in body["message"]


def test_patch_me_updates_timezone(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    access_token = register_verify_and_login(auth_client, mailer, "tz-update@example.com")
    headers = {"Authorization": f"Bearer {access_token}"}

    response = auth_client.patch(
        "/v1/auth/me",
        headers=headers,
        json={"timezone": "Europe/London"},
    )
    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/London"

    me_response = auth_client.get("/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["timezone"] == "Europe/London"


def test_patch_me_rejects_unknown_timezone(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    access_token = register_verify_and_login(auth_client, mailer, "tz-bad@example.com")

    response = auth_client.patch(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"timezone": "Not/A_Real_Zone"},
    )
    assert response.status_code == 400
    assert "Unknown timezone" in response.json()["detail"]["message"]
    assert response.json()["detail"]["code"] == "invalid_timezone"
