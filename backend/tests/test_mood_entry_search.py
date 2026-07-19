"""Semantic search API tests with mocked embeddings (no model download)."""

from __future__ import annotations

import hashlib
import math

import pytest
from app.config import settings
from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, register_verify_and_login
from tests.test_mood_entries import _auth_headers, _create_entry


def _fake_embed_texts(texts: list[str]) -> list[list[float]]:
    """Deterministic pseudo-embeddings from token hashes (384 dims)."""
    dims = settings.embedding_dims
    result: list[list[float]] = []
    for text in texts:
        vector = [0.0] * dims
        tokens = text.casefold().split()
        if not tokens:
            tokens = [text.casefold() or "empty"]
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            for i in range(0, min(len(digest), dims // 4)):
                idx = digest[i] % dims
                vector[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        result.append([x / norm for x in vector])
    return result


@pytest.fixture
def embedding_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embedding_enabled", True)
    monkeypatch.setattr(
        "app.services.embedding_service.embed_texts",
        _fake_embed_texts,
    )


def test_search_returns_semantically_related_entries(
    auth_client: TestClient,
    mailer: FakeEmailService,
    embedding_enabled: None,
) -> None:
    del embedding_enabled
    token = register_verify_and_login(auth_client, mailer, "search-mood@example.com")

    walk = _create_entry(
        auth_client,
        token,
        note="Evening walk in the park with birds singing",
        recorded_at="2026-07-01T10:00:00+03:00",
    )
    assert walk.status_code == 201
    coffee = _create_entry(
        auth_client,
        token,
        note="Morning coffee and reading a book at home",
        recorded_at="2026-07-02T10:00:00+03:00",
    )
    assert coffee.status_code == 201
    _create_entry(
        auth_client,
        token,
        note=None,
        recorded_at="2026-07-03T10:00:00+03:00",
    )

    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": "park birds outdoor stroll", "limit": 10},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 10
    assert body["offset"] == 0
    ids = [item["id"] for item in body["items"]]
    assert walk.json()["id"] in ids
    assert ids[0] == walk.json()["id"]
    assert coffee.json()["id"] in ids
    # Entries without notes have no embedding and must not appear.
    assert len(ids) == 2


def test_search_rejects_blank_query(
    auth_client: TestClient,
    mailer: FakeEmailService,
    embedding_enabled: None,
) -> None:
    del embedding_enabled
    token = register_verify_and_login(auth_client, mailer, "search-empty@example.com")
    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": "   "},
        headers=_auth_headers(token),
    )
    assert response.status_code == 400


def test_search_isolated_per_user(
    auth_client: TestClient,
    mailer: FakeEmailService,
    embedding_enabled: None,
) -> None:
    del embedding_enabled
    token_a = register_verify_and_login(auth_client, mailer, "search-a@example.com")
    token_b = register_verify_and_login(auth_client, mailer, "search-b@example.com")

    created = _create_entry(
        auth_client,
        token_a,
        note="Secret garden flowers blooming",
    )
    assert created.status_code == 201

    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": "garden flowers"},
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
