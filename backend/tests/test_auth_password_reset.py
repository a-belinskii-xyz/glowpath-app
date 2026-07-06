from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, extract_token_from_email


def test_forgot_reset_and_login_with_new_password(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    email = "reset@example.com"
    auth_client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123", "password_confirm": "password123"},
    )
    verify_token = extract_token_from_email(mailer.outbox[-1].body)
    auth_client.get(f"/v1/auth/verify-email?token={verify_token}")

    forgot_response = auth_client.post("/v1/auth/forgot-password", json={"email": email})
    assert forgot_response.status_code == 200
    forgot_body = forgot_response.json()
    assert forgot_body["status"] == "email_sent"
    assert "Password reset email sent" in forgot_body["message"]
    reset_token = extract_token_from_email(mailer.outbox[-1].body)

    reset_response = auth_client.post(
        "/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "newpassword99",
            "password_confirm": "newpassword99",
        },
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Password reset successfully"

    old_login = auth_client.post(
        "/v1/auth/login",
        json={"email": email, "password": "password123", "password_confirm": "password123"},
    )
    assert old_login.status_code == 401

    new_login = auth_client.post(
        "/v1/auth/login",
        json={"email": email, "password": "newpassword99"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_forgot_password_unknown_email_returns_request_accepted(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/v1/auth/forgot-password",
        json={"email": "missing@example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "request_accepted"
    assert "password reset link" in body["message"]
