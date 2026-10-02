"""Mood-entry search: full-text or substring match, plus optional semantic ranking."""

from __future__ import annotations

import hashlib
import math

import pytest
from app.config import settings
from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, register_verify_and_login
from tests.test_mood_entries import _auth_headers, _create_entry

LONG_NOTE = (
    "Не следует, однако, забывать о том, что курс на социально-ориентированный "
    "национальный проект представляет собой интересный эксперимент проверки "
    "соответствующих условий активизации."
)


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
    monkeypatch.setattr(settings, "embedding_search_max_distance", 0.5)
    monkeypatch.setattr(
        "app.services.embedding_service.embed_texts",
        _fake_embed_texts,
    )


def _seed_walk_and_coffee(auth_client: TestClient, token: str) -> tuple[str, str]:
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
    return walk.json()["id"], coffee.json()["id"]


def test_search_returns_semantically_related_entries(
    auth_client: TestClient,
    mailer: FakeEmailService,
    embedding_enabled: None,
) -> None:
    del embedding_enabled
    token = register_verify_and_login(auth_client, mailer, "search-mood@example.com")
    walk_id, coffee_id = _seed_walk_and_coffee(auth_client, token)

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
    assert ids == [walk_id]
    assert coffee_id not in ids


def test_search_includes_distant_entries_when_threshold_is_loose(
    auth_client: TestClient,
    mailer: FakeEmailService,
    embedding_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del embedding_enabled
    monkeypatch.setattr(settings, "embedding_search_max_distance", 2.0)
    token = register_verify_and_login(auth_client, mailer, "search-loose@example.com")
    walk_id, coffee_id = _seed_walk_and_coffee(auth_client, token)

    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": "park birds outdoor stroll", "limit": 10},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids[0] == walk_id
    assert coffee_id in ids


def test_search_finds_exact_word_in_long_note(
    auth_client: TestClient,
    mailer: FakeEmailService,
    embedding_enabled: None,
) -> None:
    del embedding_enabled
    token = register_verify_and_login(auth_client, mailer, "search-exact@example.com")
    hit = _create_entry(
        auth_client,
        token,
        note=LONG_NOTE,
        recorded_at="2026-07-04T17:59:00+03:00",
    )
    assert hit.status_code == 201
    noise = _create_entry(
        auth_client,
        token,
        note="цууццу",
        recorded_at="2026-08-17T13:59:00+03:00",
    )
    assert noise.status_code == 201

    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": "интересный", "limit": 10},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [hit.json()["id"]]
    assert noise.json()["id"] not in ids


def test_search_phrase_match_beats_semantic_threshold(
    auth_client: TestClient,
    mailer: FakeEmailService,
    embedding_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del embedding_enabled
    monkeypatch.setattr(settings, "embedding_search_max_distance", 0.01)
    token = register_verify_and_login(auth_client, mailer, "search-phrase@example.com")
    hit = _create_entry(auth_client, token, note=LONG_NOTE)
    assert hit.status_code == 201

    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": "интересный эксперимент", "limit": 10},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [hit.json()["id"]]


def test_search_substring_works_when_embeddings_disabled(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "search-no-embed@example.com")
    hit = _create_entry(auth_client, token, note=LONG_NOTE)
    assert hit.status_code == 201

    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": "интересный", "limit": 10},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [hit.json()["id"]]


def test_search_escapes_like_wildcards(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "search-wild@example.com")
    hit = _create_entry(auth_client, token, note="Progress 100% done")
    assert hit.status_code == 201
    _create_entry(auth_client, token, note="Progress 1000 done")

    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": "100%", "limit": 10},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [hit.json()["id"]]


def test_search_single_word_skips_embeddings(
    auth_client: TestClient,
    mailer: FakeEmailService,
    embedding_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del embedding_enabled
    calls: list[list[str]] = []

    def _tracking_embed(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return _fake_embed_texts(texts)

    monkeypatch.setattr("app.services.embedding_service.embed_texts", _tracking_embed)
    token = register_verify_and_login(auth_client, mailer, "search-skip-embed@example.com")
    created = _create_entry(auth_client, token, note="Morning coffee at home")
    assert created.status_code == 201
    calls.clear()

    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": "coffee", "limit": 10},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [created.json()["id"]]
    assert calls == []


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


def _search_ids(auth_client: TestClient, token: str, query: str) -> list[str]:
    response = auth_client.get(
        "/v1/mood-entries/search",
        params={"q": query, "limit": 10},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    return [item["id"] for item in response.json()["items"]]


def test_search_matches_russian_word_forms(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "search-ru-forms@example.com")
    tired = _create_entry(auth_client, token, note="Весь день чувствовала усталость")
    sad = _create_entry(auth_client, token, note="Мне сегодня грустно")
    _create_entry(auth_client, token, note="Хорошая прогулка в парке")

    assert _search_ids(auth_client, token, "устала") == [tired.json()["id"]]
    assert _search_ids(auth_client, token, "грусть") == [sad.json()["id"]]


def test_search_matches_english_word_forms(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "search-en-forms@example.com")
    hit = _create_entry(auth_client, token, note="Too many meetings, went running after work")
    _create_entry(auth_client, token, note="Quiet evening at home")

    assert _search_ids(auth_client, token, "meeting") == [hit.json()["id"]]
    assert _search_ids(auth_client, token, "run") == [hit.json()["id"]]


def test_search_keeps_substring_matches(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "search-substring@example.com")
    hit = _create_entry(auth_client, token, note="Позвонила маме вечером")

    assert _search_ids(auth_client, token, "звонил") == [hit.json()["id"]]


def test_search_stop_words_only_falls_back_to_substring(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "search-stopwords@example.com")
    hit = _create_entry(auth_client, token, note="Read the book")
    _create_entry(auth_client, token, note="Coffee")

    assert _search_ids(auth_client, token, "the") == [hit.json()["id"]]


def test_search_orders_full_text_hits_by_rank_then_date(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "search-rank@example.com")
    dense = _create_entry(
        auth_client,
        token,
        note="Тревога утром, тревога днём, тревога вечером",
        recorded_at="2026-07-01T10:00:00+03:00",
    )
    single = _create_entry(
        auth_client,
        token,
        note="Немного тревоги перед встречей и много дел",
        recorded_at="2026-07-03T10:00:00+03:00",
    )
    substring_only = _create_entry(
        auth_client,
        token,
        note="Слушала подкаст «Антитревога»",
        recorded_at="2026-07-05T10:00:00+03:00",
    )

    assert _search_ids(auth_client, token, "тревога") == [
        dense.json()["id"],
        single.json()["id"],
        substring_only.json()["id"],
    ]
