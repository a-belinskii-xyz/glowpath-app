from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def normalize_timezone(timezone_name: str) -> str:
    """Validate an IANA timezone name and return the trimmed value."""
    name = timezone_name.strip()
    if not name:
        raise ValueError("Timezone is required")
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {name}") from exc
    return name
