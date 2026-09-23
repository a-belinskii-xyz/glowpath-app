from __future__ import annotations

from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Vite/WSL/Firefox often open 127.0.0.1 (or another local port) instead of localhost.
LOCAL_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?"


class CorsSettings(Protocol):
    cors_origins: str
    frontend_url: str
    debug: bool


def parse_origin_list(value: str) -> list[str]:
    return [part.strip().rstrip("/") for part in value.split(",") if part.strip()]


def localhost_origin_aliases(origin: str) -> list[str]:
    cleaned = origin.strip().rstrip("/")
    if not cleaned:
        return []
    parsed = urlsplit(cleaned)
    host = parsed.hostname
    if host is None or host not in _LOCAL_HOSTS:
        return [cleaned]
    port_part = f":{parsed.port}" if parsed.port is not None else ""
    aliases = [
        cleaned,
        urlunsplit((parsed.scheme, f"localhost{port_part}", "", "", "")),
        urlunsplit((parsed.scheme, f"127.0.0.1{port_part}", "", "", "")),
        urlunsplit((parsed.scheme, f"[::1]{port_part}", "", "", "")),
    ]
    unique: list[str] = []
    for item in aliases:
        if item not in unique:
            unique.append(item)
    return unique


def cors_allow_origins(settings: CorsSettings) -> list[str]:
    origins: list[str] = []
    seen: set[str] = set()
    for raw in (settings.cors_origins, settings.frontend_url):
        for origin in parse_origin_list(raw):
            for alias in localhost_origin_aliases(origin):
                if alias not in seen:
                    seen.add(alias)
                    origins.append(alias)
    return origins


def cors_allow_origin_regex(settings: CorsSettings) -> str | None:
    if settings.debug:
        return LOCAL_ORIGIN_REGEX
    return None
