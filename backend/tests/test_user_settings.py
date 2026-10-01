from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_theme_preference_defaults_to_system(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "theme-default@example.com")

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.status_code == 200
    assert me.json()["theme_preference"] == "system"


def test_patch_me_updates_theme_preference_and_persists(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "theme-dark@example.com")
    original_timezone = auth_client.get("/v1/auth/me", headers=_auth_headers(token)).json()[
        "timezone"
    ]

    response = auth_client.patch(
        "/v1/auth/me",
        json={"theme_preference": "dark"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["theme_preference"] == "dark"
    assert response.json()["timezone"] == original_timezone

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.json()["theme_preference"] == "dark"


def test_patch_me_timezone_keeps_theme_preference(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "theme-tz@example.com")
    auth_client.patch(
        "/v1/auth/me",
        json={"theme_preference": "light"},
        headers=_auth_headers(token),
    )

    response = auth_client.patch(
        "/v1/auth/me",
        json={"timezone": "Europe/Berlin"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/Berlin"
    assert response.json()["theme_preference"] == "light"


def test_patch_me_rejects_unknown_theme(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "theme-bad@example.com")

    response = auth_client.patch(
        "/v1/auth/me",
        json={"theme_preference": "sepia"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 422


def test_patch_me_rejects_empty_body(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "theme-empty@example.com")

    response = auth_client.patch("/v1/auth/me", json={}, headers=_auth_headers(token))
    assert response.status_code == 422


def test_locale_is_empty_until_the_app_sends_it(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "locale-default@example.com")

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.json()["locale"] is None

    response = auth_client.patch(
        "/v1/auth/me",
        json={"locale": "ru"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["locale"] == "ru"
    assert response.json()["theme_preference"] == "system"

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.json()["locale"] == "ru"


def test_patch_me_rejects_unsupported_locale(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "locale-bad@example.com")

    response = auth_client.patch(
        "/v1/auth/me",
        json={"locale": "de"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
