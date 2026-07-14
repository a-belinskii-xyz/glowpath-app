from fastapi.testclient import TestClient

from tests.conftest import register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_default_note_templates_provisioned_on_register(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "templates-default@example.com")
    headers = _auth_headers(token)

    response = auth_client.get("/v1/note-templates", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 3
    assert [item["slug"] for item in items] == [
        "daily_reflection",
        "gratitude",
        "mood_check_in",
    ]
    assert items[0]["label"] == "Daily reflection"
    assert "What I did" in items[0]["body"]


def test_note_template_crud(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "templates-crud@example.com")
    headers = _auth_headers(token)

    created = auth_client.post(
        "/v1/note-templates",
        json={
            "labels": {"en": "Custom template"},
            "bodies": {"en": "## Focus\n\n"},
        },
        headers=headers,
    )
    assert created.status_code == 201
    template = created.json()
    assert template["slug"] == "custom_template"
    assert template["label"] == "Custom template"
    assert template["body"] == "## Focus"
    template_id = template["id"]

    patched = auth_client.patch(
        f"/v1/note-templates/{template_id}",
        json={
            "labels": {"en": "Updated template"},
            "bodies": {"en": "## Updated\n\nNotes here"},
        },
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["label"] == "Updated template"
    assert "Updated" in patched.json()["body"]

    deleted = auth_client.delete(f"/v1/note-templates/{template_id}", headers=headers)
    assert deleted.status_code == 204

    listed = auth_client.get("/v1/note-templates", headers=headers)
    assert listed.status_code == 200
    assert all(item["id"] != template_id for item in listed.json()["items"])


def test_note_template_locale_resolution(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "templates-locale@example.com")
    headers = {**_auth_headers(token), "Accept-Language": "ru"}

    response = auth_client.get("/v1/note-templates", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    daily = next(item for item in items if item["slug"] == "daily_reflection")
    assert daily["label"] == "Дневная рефлексия"
    assert "Что я делал" in daily["body"]


def test_reorder_note_templates(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "templates-reorder@example.com")
    headers = _auth_headers(token)

    listed = auth_client.get("/v1/note-templates", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    ordered_ids = [items[-1]["id"], *[item["id"] for item in items[:-1]]]

    reordered = auth_client.put(
        "/v1/note-templates/reorder",
        json={"ordered_ids": ordered_ids},
        headers=headers,
    )
    assert reordered.status_code == 200
    assert [item["id"] for item in reordered.json()["items"]] == ordered_ids
