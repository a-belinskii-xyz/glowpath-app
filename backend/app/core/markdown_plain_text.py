"""Plain-text length for markdown notes (formatting markers do not count)."""

from __future__ import annotations

import re

NOTE_CONTENT_MAX_LENGTH = 500
NOTE_RAW_MAX_LENGTH = 4000

_FENCED_CODE = re.compile(r"```[^\n]*\n?(.*?)```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]+)`")
_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BLOCKQUOTE = re.compile(r"^>\s?", re.MULTILINE)
_UNORDERED_LIST = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
_ORDERED_LIST = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
_BOLD = re.compile(r"(\*\*|__)(.+?)\1")
_ITALIC = re.compile(r"(\*|_)(.+?)\1")
_STRIKE = re.compile(r"~~(.+?)~~")
_HORIZONTAL_RULE = re.compile(r"^([-*_]){3,}\s*$", re.MULTILINE)


def markdown_to_plain_text(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n")
    text = _FENCED_CODE.sub(r"\1", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _IMAGE.sub(r"\1", text)
    text = _LINK.sub(r"\1", text)
    text = _HEADING.sub("", text)
    text = _BLOCKQUOTE.sub("", text)
    text = _UNORDERED_LIST.sub("", text)
    text = _ORDERED_LIST.sub("", text)
    text = _HORIZONTAL_RULE.sub("", text)
    text = _BOLD.sub(r"\2", text)
    text = _ITALIC.sub(r"\2", text)
    text = _STRIKE.sub(r"\1", text)
    return text


def markdown_content_length(markdown: str) -> int:
    return len(markdown_to_plain_text(markdown))
