"""Achievement condition specs: what params each criteria type takes and how to validate them.

The staff editor renders its condition form from ``CRITERIA_SPECS`` (served by the
staff API), so a new condition type needs an evaluator in
``services/achievements/criteria.py`` plus one entry here and its labels on the
frontend. Composite conditions (``all`` / ``any`` over a list of these) can be added
later as types whose param is a list of nested criteria.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.achievements import CriteriaType
from app.core.attachment_kind import AttachmentKind

MAX_CRITERIA_COUNT = 100_000


class CriteriaParamKind(StrEnum):
    INT = "int"
    CHOICE = "choice"


@dataclass(frozen=True, slots=True)
class CriteriaParam:
    name: str
    kind: CriteriaParamKind
    required: bool = True
    minimum: int | None = None
    maximum: int | None = None
    choices: tuple[str | int, ...] = ()
    default: int | str | None = None


@dataclass(frozen=True, slots=True)
class CriteriaSpec:
    type: CriteriaType
    params: tuple[CriteriaParam, ...]
    # At least one of these optional params must be set (calendar_match).
    require_any_of: tuple[str, ...] = ()


class InvalidCriteriaError(ValueError):
    def __init__(self, message: str, *, param: str | None = None) -> None:
        super().__init__(message)
        self.param = param


def _count(name: str = "count", *, maximum: int = MAX_CRITERIA_COUNT) -> CriteriaParam:
    return CriteriaParam(name, CriteriaParamKind.INT, minimum=1, maximum=maximum, default=1)


def _hour(name: str) -> CriteriaParam:
    return CriteriaParam(name, CriteriaParamKind.INT, minimum=0, maximum=23, default=0)


_SPECS: tuple[CriteriaSpec, ...] = (
    CriteriaSpec(CriteriaType.ENTRY_COUNT, (_count(),)),
    CriteriaSpec(CriteriaType.CONSECUTIVE_DAYS, (_count("days", maximum=3650),)),
    CriteriaSpec(CriteriaType.DISTINCT_CHECKIN_DAYS, (_count(),)),
    CriteriaSpec(CriteriaType.ENTRIES_WITH_NOTE, (_count(),)),
    CriteriaSpec(CriteriaType.FAVORITE_COUNT, (_count(),)),
    CriteriaSpec(
        CriteriaType.SCORE_COUNT,
        (
            CriteriaParam("score", CriteriaParamKind.INT, minimum=1, maximum=5, default=5),
            _count(),
        ),
    ),
    CriteriaSpec(CriteriaType.DISTINCT_SCORES, (_count(maximum=5),)),
    CriteriaSpec(
        CriteriaType.ATTACHMENT_COUNT,
        (
            CriteriaParam(
                "kind",
                CriteriaParamKind.CHOICE,
                required=False,
                choices=tuple(kind.value for kind in AttachmentKind),
            ),
            _count(),
        ),
    ),
    CriteriaSpec(CriteriaType.TAGGED_ENTRY_COUNT, (_count(),)),
    CriteriaSpec(CriteriaType.DISTINCT_TAGS_USED, (_count(),)),
    CriteriaSpec(CriteriaType.GOAL_CREATED_COUNT, (_count(),)),
    CriteriaSpec(CriteriaType.GOAL_CHECKIN_COUNT, (_count(),)),
    CriteriaSpec(
        CriteriaType.SOURCE_PREFIX,
        (
            CriteriaParam(
                "prefix",
                CriteriaParamKind.CHOICE,
                choices=("telegram", "email"),
                default="telegram",
            ),
            _count(),
        ),
    ),
    CriteriaSpec(
        CriteriaType.LOCAL_HOUR_RANGE,
        (_hour("hour_from"), _hour("hour_to"), _count()),
    ),
    CriteriaSpec(
        CriteriaType.CALENDAR_MATCH,
        (
            CriteriaParam(
                "weekday",
                CriteriaParamKind.CHOICE,
                required=False,
                choices=(0, 1, 2, 3, 4, 5, 6),
            ),
            CriteriaParam("month", CriteriaParamKind.INT, required=False, minimum=1, maximum=12),
            CriteriaParam("day", CriteriaParamKind.INT, required=False, minimum=1, maximum=31),
        ),
        require_any_of=("weekday", "month", "day"),
    ),
)

CRITERIA_SPECS: dict[str, CriteriaSpec] = {spec.type.value: spec for spec in _SPECS}


def _normalize_param(param: CriteriaParam, raw: Any) -> int | str:
    if param.kind is CriteriaParamKind.CHOICE:
        for choice in param.choices:
            if raw == choice or (isinstance(choice, int) and str(raw) == str(choice)):
                return choice
        raise InvalidCriteriaError(f"{param.name} must be one of {param.choices}", param=param.name)

    if isinstance(raw, bool):
        raise InvalidCriteriaError(f"{param.name} must be an integer", param=param.name)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise InvalidCriteriaError(f"{param.name} must be an integer", param=param.name) from exc
    if isinstance(raw, float) and raw != value:
        raise InvalidCriteriaError(f"{param.name} must be an integer", param=param.name)
    if param.minimum is not None and value < param.minimum:
        raise InvalidCriteriaError(f"{param.name} must be >= {param.minimum}", param=param.name)
    if param.maximum is not None and value > param.maximum:
        raise InvalidCriteriaError(f"{param.name} must be <= {param.maximum}", param=param.name)
    return value


def normalize_criteria(raw: Any) -> dict[str, Any]:
    """Validate a criteria dict against its spec and drop unknown keys."""
    if not isinstance(raw, dict):
        raise InvalidCriteriaError("criteria must be an object")
    spec = CRITERIA_SPECS.get(str(raw.get("type")))
    if spec is None:
        raise InvalidCriteriaError("Unknown criteria type", param="type")

    normalized: dict[str, Any] = {"type": spec.type.value}
    for param in spec.params:
        value = raw.get(param.name)
        if value is None or value == "":
            if param.required:
                raise InvalidCriteriaError(f"{param.name} is required", param=param.name)
            continue
        normalized[param.name] = _normalize_param(param, value)

    if spec.require_any_of and not any(name in normalized for name in spec.require_any_of):
        raise InvalidCriteriaError(
            f"Set at least one of {', '.join(spec.require_any_of)}",
            param=spec.require_any_of[0],
        )
    if (
        spec.type is CriteriaType.LOCAL_HOUR_RANGE
        and normalized["hour_from"] == normalized["hour_to"]
    ):
        raise InvalidCriteriaError("hour_from and hour_to must differ", param="hour_to")
    return normalized


def serialize_criteria_specs() -> list[dict[str, Any]]:
    return [
        {
            "type": spec.type.value,
            "require_any_of": list(spec.require_any_of),
            "params": [
                {
                    "name": param.name,
                    "kind": param.kind.value,
                    "required": param.required,
                    "minimum": param.minimum,
                    "maximum": param.maximum,
                    "choices": list(param.choices),
                    "default": param.default,
                }
                for param in spec.params
            ],
        }
        for spec in _SPECS
    ]
