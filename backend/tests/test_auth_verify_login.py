from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, extract_token_from_email


def _register_and_get_verify_token(
    auth_client: TestClient,
    mailer: FakeEmailService,
    email: str,
) -> str:
    response = auth_client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123"},
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
        json={"email": email, "password": "password123"},
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

    login_response = auth_client.post(
        "/v1/auth/login",
        json={"email": email, "password": "password123"},
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
