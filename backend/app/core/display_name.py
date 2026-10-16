import unicodedata

DISPLAY_NAME_MAX_LENGTH = 40


def normalize_display_name(raw: str | None) -> str | None:
    """Trim and collapse whitespace, drop control characters; blank means no name."""
    if raw is None:
        return None
    cleaned = "".join(ch for ch in raw if not unicodedata.category(ch).startswith("C"))
    collapsed = " ".join(cleaned.split())[:DISPLAY_NAME_MAX_LENGTH].strip()
    return collapsed or None
