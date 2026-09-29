"""Single-emoji validation for user-chosen icons (tags, goals, mood scores).

Accepts exactly one emoji "grapheme": a pictographic character with optional
variation selector / skin tone, ZWJ sequences (👨‍👩‍👧), flags (🇷🇺), subdivision
flags (🏴 + tag chars) and keycaps (1️⃣). Plain text, digits, punctuation and
multiple emoji are rejected.
"""

from __future__ import annotations

_VS16 = 0xFE0F
_ZWJ = 0x200D
_KEYCAP = 0x20E3
_TAG_CANCEL = 0xE007F
_KEYCAP_BASES = frozenset("0123456789#*")

# Approximation of Unicode Extended_Pictographic (enough for every RGI emoji base).
_PICTOGRAPHIC_RANGES: tuple[tuple[int, int], ...] = (
    (0x00A9, 0x00A9),
    (0x00AE, 0x00AE),
    (0x203C, 0x203C),
    (0x2049, 0x2049),
    (0x2122, 0x2122),
    (0x2139, 0x2139),
    (0x2194, 0x2199),
    (0x21A9, 0x21AA),
    (0x231A, 0x231B),
    (0x2328, 0x2328),
    (0x2388, 0x2388),
    (0x23CF, 0x23CF),
    (0x23E9, 0x23F3),
    (0x23F8, 0x23FA),
    (0x24C2, 0x24C2),
    (0x25AA, 0x25AB),
    (0x25B6, 0x25B6),
    (0x25C0, 0x25C0),
    (0x25FB, 0x25FE),
    (0x2600, 0x27BF),
    (0x2934, 0x2935),
    (0x2B05, 0x2B07),
    (0x2B1B, 0x2B1C),
    (0x2B50, 0x2B50),
    (0x2B55, 0x2B55),
    (0x3030, 0x3030),
    (0x303D, 0x303D),
    (0x3297, 0x3297),
    (0x3299, 0x3299),
    (0x1F000, 0x1F1E5),
    (0x1F200, 0x1F3FA),
    (0x1F400, 0x1FAFF),
    (0x1FC00, 0x1FFFD),
)


def _is_pictographic(cp: int) -> bool:
    return any(start <= cp <= end for start, end in _PICTOGRAPHIC_RANGES)


def _is_regional_indicator(cp: int) -> bool:
    return 0x1F1E6 <= cp <= 0x1F1FF


def _is_skin_tone(cp: int) -> bool:
    return 0x1F3FB <= cp <= 0x1F3FF


def _is_tag_char(cp: int) -> bool:
    return 0xE0020 <= cp <= 0xE007E


def _is_keycap(cps: list[int]) -> bool:
    if len(cps) == 2:
        return chr(cps[0]) in _KEYCAP_BASES and cps[1] == _KEYCAP
    if len(cps) == 3:
        return chr(cps[0]) in _KEYCAP_BASES and cps[1] == _VS16 and cps[2] == _KEYCAP
    return False


def _consume_element(cps: list[int], i: int) -> int | None:
    """Consume one pictographic element starting at ``i``; return next index."""
    if i >= len(cps) or not _is_pictographic(cps[i]):
        return None
    i += 1
    if i < len(cps) and cps[i] == _VS16:
        i += 1
    if i < len(cps) and _is_skin_tone(cps[i]):
        i += 1
    return i


def is_single_emoji(value: str) -> bool:
    cps = [ord(ch) for ch in value]
    if not cps:
        return False
    if _is_keycap(cps):
        return True
    if len(cps) == 2 and all(_is_regional_indicator(cp) for cp in cps):
        return True
    # Lone skin tone swatch (🏽) is a valid emoji on its own.
    if len(cps) == 1 and _is_skin_tone(cps[0]):
        return True

    i = _consume_element(cps, 0)
    if i is None:
        return False
    # Subdivision flag: 🏴 followed by tag characters and a cancel tag.
    if i < len(cps) and _is_tag_char(cps[i]):
        while i < len(cps) and _is_tag_char(cps[i]):
            i += 1
        return i == len(cps) - 1 and cps[i] == _TAG_CANCEL
    while i < len(cps):
        if cps[i] != _ZWJ:
            return False
        next_i = _consume_element(cps, i + 1)
        if next_i is None:
            return False
        i = next_i
    return True
