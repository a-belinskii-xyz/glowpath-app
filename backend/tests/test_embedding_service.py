"""Unit tests for embedding text corpus builders (no model download)."""

from types import SimpleNamespace

from app.services.embedding_service import build_entry_search_text


def test_build_entry_search_text_note_only() -> None:
    entry = SimpleNamespace(note="**Hello** world", attachments=[])
    assert build_entry_search_text(entry) == "Hello world"


def test_build_entry_search_text_includes_transcription() -> None:
    entry = SimpleNamespace(
        note="Walk in the park",
        attachments=[
            SimpleNamespace(transcription="  birds singing  "),
            SimpleNamespace(transcription=None),
            SimpleNamespace(transcription=""),
        ],
    )
    assert build_entry_search_text(entry) == "Walk in the park\nbirds singing"


def test_build_entry_search_text_empty() -> None:
    entry = SimpleNamespace(note=None, attachments=[SimpleNamespace(transcription="  ")])
    assert build_entry_search_text(entry) is None


def test_build_entry_search_text_markdown_stripped() -> None:
    entry = SimpleNamespace(note="- one\n- two", attachments=[])
    assert build_entry_search_text(entry) == "one\ntwo"
