from app.core.default_goals import DEFAULT_GOALS
from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
from app.core.onboarding_packs import compose_additive_suggestions
from app.models.note_template import NoteTemplate
from app.models.tag_group import TagGroup
from app.models.user import User
from app.services.user_provisioning import count_user_goals, count_user_tag_groups
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_onboarding_catalog_returns_localized_questions(auth_client: TestClient) -> None:
    response = auth_client.get("/v1/onboarding/catalog", headers={"Accept-Language": "ru"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["questions"]) == 3
    assert body["questions"][0]["block_id"] == "life"
    title = body["questions"][0]["title"]
    assert "Чем" in title or "занят" in title.lower()


def test_onboarding_suggestions_exclude_goals_and_base(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "onboard-sugg@example.com")
    response = auth_client.post(
        "/v1/onboarding/suggestions",
        headers={**_auth_headers(token), "Accept-Language": "en"},
        json={"option_keys": ["life.office", "focus.stress", "interest.gaming"]},
    )
    assert response.status_code == 200
    body = response.json()
    group_slugs = {group["slug"] for group in body["tag_groups"]}
    assert "work_context" in group_slugs
    assert "gaming" in group_slugs
    assert "mood" not in group_slugs
    assert "weather" not in group_slugs
    assert any(item["slug"] == "workday_reflection" for item in body["note_templates"])
    workday = next(item for item in body["note_templates"] if item["slug"] == "workday_reflection")
    assert "accomplish" in workday["body"].lower() or "What" in workday["body"]
    assert "goals" not in body


def test_onboarding_skip_marks_completed(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "onboard-skip@example.com")
    user = db.scalar(select(User).where(User.email == "onboard-skip@example.com"))
    assert user is not None
    assert user.onboarding_completed_at is None
    assert count_user_tag_groups(db, user.id) == len(DEFAULT_TAG_GROUPS)

    response = auth_client.post(
        "/v1/onboarding/complete",
        headers=_auth_headers(token),
        json={"skip": True, "option_keys": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["onboarding_completed"] is True
    assert body["onboarding_completed_at"] is not None

    db.refresh(user)
    assert user.onboarding_completed_at is not None
    assert count_user_tag_groups(db, user.id) == len(DEFAULT_TAG_GROUPS)
    assert count_user_goals(db, user.id) == len(DEFAULT_GOALS)


def test_onboarding_complete_adds_only_selected_items(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "onboard-packs@example.com")
    user = db.scalar(select(User).where(User.email == "onboard-packs@example.com"))
    assert user is not None
    goals_before = count_user_goals(db, user.id)

    suggestions = compose_additive_suggestions(
        option_keys=["life.office", "focus.stress", "interest.gaming"]
    )
    assert any(group.slug == "gaming" for group in suggestions.tag_groups)

    response = auth_client.post(
        "/v1/onboarding/complete",
        headers=_auth_headers(token),
        json={
            "skip": False,
            "option_keys": ["life.office", "focus.stress", "interest.gaming"],
            "tag_group_slugs": ["gaming"],
            "note_template_slugs": ["after_session_notes"],
        },
    )
    assert response.status_code == 200
    assert response.json()["onboarding_completed"] is True

    group_slugs = set(db.scalars(select(TagGroup.slug).where(TagGroup.user_id == user.id)).all())
    assert "gaming" in group_slugs
    assert "work_context" not in group_slugs
    assert "coping" not in group_slugs

    template_slugs = set(
        db.scalars(select(NoteTemplate.slug).where(NoteTemplate.user_id == user.id)).all()
    )
    assert "after_session_notes" in template_slugs
    assert "workday_reflection" not in template_slugs
    assert count_user_goals(db, user.id) == goals_before

    visible_count = db.scalar(
        select(func.count())
        .select_from(TagGroup)
        .where(TagGroup.user_id == user.id, TagGroup.show_on_entry.is_(True))
    )
    assert int(visible_count or 0) <= 6


def test_onboarding_complete_rejects_unknown_suggestion_slug(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "onboard-bad-sel@example.com")
    response = auth_client.post(
        "/v1/onboarding/complete",
        headers=_auth_headers(token),
        json={
            "skip": False,
            "option_keys": ["life.office"],
            "tag_group_slugs": ["gaming"],
            "note_template_slugs": [],
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_onboarding_options"


def test_onboarding_complete_twice_returns_409(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "onboard-twice@example.com")
    first = auth_client.post(
        "/v1/onboarding/complete",
        headers=_auth_headers(token),
        json={"skip": True},
    )
    assert first.status_code == 200
    second = auth_client.post(
        "/v1/onboarding/complete",
        headers=_auth_headers(token),
        json={"skip": True},
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "onboarding_already_completed"


def test_onboarding_rejects_unknown_options(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "onboard-bad@example.com")
    response = auth_client.post(
        "/v1/onboarding/complete",
        headers=_auth_headers(token),
        json={"skip": False, "option_keys": ["life.not_a_real_option"]},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_onboarding_options"
